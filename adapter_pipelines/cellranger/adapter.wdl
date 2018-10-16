import "cellranger.wdl" as CellRanger
import "submit.wdl" as submit_wdl


task GetInputs {
  String bundle_uuid
  String bundle_version
  String dss_url
  Int? retry_timeout
  Float? retry_multiplier
  Int? retry_max_interval
  Int? individual_request_timeout
  Boolean record_http
  String pipeline_tools_version

  command <<<
    export RECORD_HTTP_REQUESTS="${record_http}"
    export RETRY_TIMEOUT="${retry_timeout}"
    export RETRY_MULTIPLIER="${retry_multiplier}"
    export RETRY_MAX_INTERVAL="${retry_max_interval}"
    export INDIVIDUAL_REQUEST_TIMEOUT="${individual_request_timeout}"

    # Force the binary layer of the stdout and stderr streams to be unbuffered.
    python -u <<CODE
    from pipeline_tools import input_utils

    input_utils.create_optimus_input_tsv(
                    "${bundle_uuid}",
                    "${bundle_version}",
                    "${dss_url}")

    CODE
  >>>
  runtime {
    docker: "quay.io/humancellatlas/secondary-analysis-pipeline-tools:" + pipeline_tools_version
  }
  output {
    String sample_id = read_string("sample_id.txt")
    Array[File] r1_fastq = read_lines("r1.txt")
    Array[File] r2_fastq = read_lines("r2.txt")
    Array[File] i1_fastq = read_lines("i1.txt")
    Array[Int] lanes = read_lines("lanes.txt")
    Array[File] http_requests = glob("request_*.txt")
    Array[File] http_responses = glob("response_*.txt")
  }
}

task RenameFastqFiles {
    File r1
    File r2
    File i1
    String sample_id
    String lane
    String pipeline_tools_version

    command <<<
      mv ${r1} '${sample_id}_S1_L00${lane}_R1_001.fastq.gz'
      mv ${r2} '${sample_id}_S1_L00${lane}_R2_001.fastq.gz'
      mv ${i1} '${sample_id}_S1_L00${lane}_I1_001.fastq.gz'
      >>>
      runtime {
        docker: "quay.io/humancellatlas/secondary-analysis-pipeline-tools:" + pipeline_tools_version
      }
      output {
        File r1_new = "${sample_id}_S1_L00${lane}_R1_001.fastq.gz"
        File r2_new = "${sample_id}_S1_L00${lane}_R2_001.fastq.gz"
        File i1_new = "${sample_id}_S1_L00${lane}_I1_001.fastq.gz"
      }
}

task RenameFiles {
    Array[File] file_paths
    Array[String] new_file_names
    String pipeline_tools_version

    command <<<
      python -u <<CODE
      import subprocess

      files=["${sep='","' file_paths}"]
      file_names=["${sep='","' new_file_names}"]

      for idx, f in enumerate(files):
          subprocess.check_output(['mv', f, file_names[idx]])

      CODE
    >>>
    runtime {
      docker: "quay.io/humancellatlas/secondary-analysis-pipeline-tools:" + pipeline_tools_version
    }
    output {
      Array[File] outputs = new_file_names
    }
}

task InputsForSubmit {
    Array[File] fastqs
    Array[Object] other_inputs
    Int? expect_cells
    String pipeline_tools_version

    command <<<
      # Force the binary layer of the stdout and stderr streams to be unbuffered.
      python -u <<CODE

      inputs = []

      print('fastq_files')
      inputs.append({"name": "fastqs", "value": "${sep=', ' fastqs}"})

      print('other inputs')
      with open('${write_objects(other_inputs)}') as f:
          keys = f.readline().strip().split('\t')
          for line in f:
              values = line.strip().split('\t')
              input = {}
              for i, key in enumerate(keys):
                  input[key] = values[i]
              print(input)
              inputs.append(input)

      print('expect cells')
      if "${expect_cells}":
          inputs.append({"name": "expect_cells", "value": "${expect_cells}"})

      print('write inputs.tsv')
      with open('inputs.tsv', 'w') as f:
          f.write('name\tvalue\n')
          for input in inputs:
              print(input)
              f.write('{0}\t{1}\n'.format(input['name'], input['value']))
      print('finished')
      CODE
    >>>

    runtime {
      docker: "quay.io/humancellatlas/secondary-analysis-pipeline-tools:" + pipeline_tools_version
    }

    output {
      File inputs = "inputs.tsv"
    }
}

workflow Adapter10xCount {
  String bundle_uuid
  String bundle_version

  String reference_name
  File transcriptome_tar_gz
  Int? expect_cells

  # Submission
  File format_map
  String dss_url
  String submit_url
  String method
  String schema_url
  String cromwell_url
  String analysis_process_schema_version
  String analysis_protocol_schema_version
  String analysis_file_version
  String run_type
  Int? retry_max_interval
  Float? retry_multiplier
  Int? retry_timeout
  Int? individual_request_timeout
  String reference_bundle
  Boolean use_caas

  # Set runtime environment such as "dev" or "staging" or "prod" so submit task could choose proper docker image to use
  String runtime_environment
  # By default, don't record http requests, unless we override in inputs json
  Boolean record_http = false
  Int max_cromwell_retries = 0
  Boolean add_md5s = false

  String pipeline_tools_version = "v0.35.0"

  call GetInputs {
    input:
      bundle_uuid = bundle_uuid,
      bundle_version = bundle_version,
      dss_url = dss_url,
      retry_multiplier = retry_multiplier,
      retry_max_interval = retry_max_interval,
      retry_timeout = retry_timeout,
      individual_request_timeout = individual_request_timeout,
      record_http = record_http,
      pipeline_tools_version = pipeline_tools_version
  }

  # Cellranger code in 10x count wdl requires files to be named a certain way.
  # To accommodate that, RenameFastqFiles copies the blue box files into the
  # cromwell execution bucket but with the names cellranger expects.
  # Putting this in its own task lets us take advantage of automatic localizing
  # and delocalizing by Cromwell/JES to actually read and write stuff in buckets.
  # TODO: Replace scatter with a for-loop inside of the task to avoid creating a
  # VM for each set of files that needs to be renamed
  scatter(i in range(length(GetInputs.lanes))) {
    call RenameFastqFiles as prep {
      input:
        r1 = GetInputs.r1_fastq[i],
        r2 = GetInputs.r2_fastq[i],
        i1 = GetInputs.i1_fastq[i],
        sample_id = GetInputs.sample_id,
        lane = GetInputs.lanes[i],
        pipeline_tools_version = pipeline_tools_version
      }
    }

  # CellRanger gets the paths to the fastq directories from the array of fastqs,
  # so the order of those files does not matter
  call CellRanger.CellRanger as analysis {
    input:
      sample_id = GetInputs.sample_id,
      fastqs = flatten([prep.r1_new, prep.r2_new, prep.i1_new]),
      reference_name = reference_name,
      transcriptome_tar_gz = transcriptome_tar_gz,
      expect_cells = expect_cells
  }

  call InputsForSubmit {
    input:
      fastqs = flatten([GetInputs.r1_fastq, GetInputs.r2_fastq, GetInputs.i1_fastq]),
      other_inputs = [
        {
          "name": "sample_id",
          "value": GetInputs.sample_id
        },
        {
          "name": "reference_name",
          "value": reference_name
        },
        {
          "name": "transcriptome_tar_gz",
          "value": transcriptome_tar_gz
        }
      ],
      expect_cells = expect_cells,
      pipeline_tools_version = pipeline_tools_version
  }

  # Rename analysis files so that all the file names are unique. For example, rename
  # "${sample_id}/outs/raw_gene_bc_matrices/${reference}/barcodes.tsv" to "raw_barcodes.tsv" so that
  # it does not overwrite "${sample_id}/outs/filtered_gene_bc_matrices/${reference}/barcodes.tsv"
  # when uploading files
  call RenameFiles as output_files {
    input:
      file_paths = [analysis.raw_barcodes, analysis.raw_genes, analysis.raw_matrix],
      new_file_names = ["raw_barcodes.tsv", "raw_genes.tsv", "raw_matrix.mtx"],
      pipeline_tools_version = pipeline_tools_version
  }

  Array[Object] inputs = read_objects(InputsForSubmit.inputs)

  call submit_wdl.submit {
    input:
      inputs = inputs,
      outputs = flatten([[
        analysis.qc,
        analysis.sorted_bam,
        analysis.sorted_bam_index,
        analysis.barcodes,
        analysis.genes,
        analysis.matrix,
        analysis.filtered_gene_h5,
        analysis.raw_gene_h5,
        analysis.mol_info_h5,
        analysis.web_summary
      ], output_files.outputs]),
      format_map = format_map,
      submit_url = submit_url,
      cromwell_url = cromwell_url,
      input_bundle_uuid = bundle_uuid,
      reference_bundle = reference_bundle,
      run_type = run_type,
      schema_url = schema_url,
      analysis_process_schema_version = analysis_process_schema_version,
      analysis_protocol_schema_version = analysis_protocol_schema_version,
      analysis_file_version = analysis_file_version,
      method = method,
      retry_multiplier = retry_multiplier,
      retry_max_interval = retry_max_interval,
      retry_timeout = retry_timeout,
      individual_request_timeout = individual_request_timeout,
      runtime_environment = runtime_environment,
      use_caas = use_caas,
      record_http = record_http,
      pipeline_tools_version = pipeline_tools_version,
      add_md5s = add_md5s,
      pipeline_version = analysis.pipeline_version,
      # The sorted bam is the largest output. Other outputs will increase space by ~50%.
      # Factor of 2 and addition of 50 GB gives some buffer.
      disk_space = ceil(size(analysis.sorted_bam, "GB") * 2 + 50)
  }
}