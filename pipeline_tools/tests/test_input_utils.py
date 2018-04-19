import unittest
import json
import os
import pytest
from pipeline_tools import input_utils
from pipeline_tools import dcp_utils


class TestInputUtils(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        with open(self.data_file('metadata/v4/ss2_assay.json')) as f:
            self.ss2_assay_json_v4 = json.load(f)
        with open(self.data_file('metadata/v4/ss2_manifest.json')) as f:
            self.ss2_manifest_json_v4 = json.load(f)
            self.ss2_manifest_files_v4 = dcp_utils.get_manifest_file_dicts(self.ss2_manifest_json_v4)
        with open(self.data_file('metadata/v5/ss2_manifest.json')) as f:
            self.ss2_manifest_json_v5 = json.load(f)
            self.ss2_manifest_files_v5 = dcp_utils.get_manifest_file_dicts(self.ss2_manifest_json_v5)
        with open(self.data_file('metadata/v5/ss2_files.json')) as f:
            self.ss2_files_json_v5 = json.load(f)
        with open(self.data_file('metadata/v4/optimus_assay.json')) as f:
            self.optimus_assay_json_v4 = json.load(f)
        with open(self.data_file('metadata/v4/optimus_manifest.json')) as f:
            self.optimus_manifest_json_v4 = json.load(f)
        with open(self.data_file('metadata/v5/ss2_links.json')) as f:
            self.links_json_v5 = json.load(f)
        with open(self.data_file('metadata/v5/ss2_links_extra_sample.json')) as f:
            self.links_json_v5_extra_sample = json.load(f)
        with open(self.data_file('metadata/v5/ss2_links_no_sample.json')) as f:
            self.links_json_v5_no_sample = json.load(f)

    def test_get_sample_id_v4(self):
        sample_id = input_utils.get_sample_id(self.ss2_assay_json_v4, '4.x')
        self.assertEqual(sample_id, 'b0c57b9c-860b-4bbf-84aa-5f845508101d')

    def test_get_sample_id_v5(self):
        sample_id = input_utils.get_sample_id(self.links_json_v5, '5.2.1')
        self.assertEqual(sample_id, 'test_sample_id')

    def test_get_sample_id_v5_extra_sample_raises_error(self):
        with self.assertRaises(ValueError):
            input_utils.get_sample_id(self.links_json_v5_extra_sample, '5.2.1')

    def test_get_sample_id_v5_missing_sample_raises_error(self):
        with self.assertRaises(ValueError):
            input_utils.get_sample_id(self.links_json_v5_no_sample, '5.2.1')

    def test_get_sample_id_non_existent_version_raises_error(self):
        with self.assertRaises(NotImplementedError):
            input_utils.get_sample_id(self.ss2_assay_json_v4, '-1')

    def test_get_input_metadata_file_uuid_v4(self):
        uuid = input_utils.get_input_metadata_file_uuid(self.ss2_manifest_files_v4, '4.x')
        self.assertEqual(uuid, 'e56638c7-f026-42d0-9be8-24b71a7d6e86')

    def test_get_input_metadata_file_uuid_v5(self):
        uuid = input_utils.get_input_metadata_file_uuid(self.ss2_manifest_files_v5, '5.2.1')
        self.assertEqual(uuid, 'file_json_uuid')

    def test_get_sample_id_file_uuid_v4(self):
        uuid = input_utils.get_sample_id_file_uuid(self.ss2_manifest_files_v4, '4.x')
        self.assertEqual(uuid, 'e56638c7-f026-42d0-9be8-24b71a7d6e86')

    def test_get_sample_id_file_uuid_v5(self):
        uuid = input_utils.get_sample_id_file_uuid(self.ss2_manifest_files_v5, '5.2.1')
        self.assertEqual(uuid, 'links_json_uuid')

    def test_is_v5_or_higher_v4_6_1(self):
        name_to_meta = self.ss2_manifest_files_v4['name_to_meta']
        is_v5_or_higher = input_utils.is_v5_or_higher(name_to_meta)
        self.assertEqual(is_v5_or_higher, False)

    def test_is_v5_or_higher_v5_2_1(self):
        name_to_meta = self.ss2_manifest_files_v5['name_to_meta']
        is_v5_or_higher = input_utils.is_v5_or_higher(name_to_meta)
        self.assertEqual(is_v5_or_higher, True)

    def test_is_v5_or_higher_missing_files(self):
        name_to_meta = {}
        with self.assertRaises(ValueError):
            input_utils.is_v5_or_higher(name_to_meta)

    def test_get_smart_seq_2_fastq_names_v4(self):
        fastq_1_name, fastq_2_name = input_utils.get_smart_seq_2_fastq_names(self.ss2_assay_json_v4, '4.x')
        self.assertEqual(fastq_1_name, 'R1.fastq.gz')
        self.assertEqual(fastq_2_name, 'R2.fastq.gz')

    def test_get_smart_seq_2_fastq_names_v5(self):
        fastq_1_name, fastq_2_name = input_utils.get_smart_seq_2_fastq_names(self.ss2_files_json_v5, '5.2.1')
        self.assertEqual(fastq_1_name, 'R1.fastq.gz')
        self.assertEqual(fastq_2_name, 'R2.fastq.gz')

    @pytest.mark.latest_schema
    def test_detect_schema_version(self):
        with open(self.data_file('metadata/latest/ss2/file.json')) as f:
            ss2_file_json_latest = json.load(f)
        version = input_utils.detect_schema_version(ss2_file_json_latest)
        parts = version.split('.')
        self.assertEqual(len(parts), 3)
        self.assertGreaterEqual(int(parts[0]), 5)

    @pytest.mark.latest_schema
    def test_get_smart_seq_2_fastq_names_latest(self):
        with open(self.data_file('metadata/latest/ss2/file.json')) as f:
            ss2_files_json_latest = json.load(f)
        fastq_1_name, fastq_2_name = input_utils.get_smart_seq_2_fastq_names(ss2_files_json_latest, '5.x')
        self.assertEqual(fastq_1_name, 'R1.fastq.gz')
        self.assertEqual(fastq_2_name, 'R2.fastq.gz')

    def test_get_optimus_lanes_v4(self):
        lanes = input_utils.get_optimus_lanes(self.optimus_assay_json_v4, '4.x')
        self.assertEqual(len(lanes), 2)
        self.assertEqual(lanes[0]['r1'], 'pbmc8k_S1_L007_R1_001.fastq.gz')
        self.assertEqual(lanes[0]['r2'], 'pbmc8k_S1_L007_R2_001.fastq.gz')
        self.assertEqual(lanes[0]['i1'], 'pbmc8k_S1_L007_I1_001.fastq.gz')
        self.assertEqual(lanes[1]['r1'], 'pbmc8k_S1_L008_R1_001.fastq.gz')
        self.assertEqual(lanes[1]['r2'], 'pbmc8k_S1_L008_R2_001.fastq.gz')
        self.assertEqual(lanes[1]['i1'], 'pbmc8k_S1_L008_I1_001.fastq.gz')

    def test_get_optimus_lanes_v5(self):
        with self.assertRaises(NotImplementedError):
            input_utils.get_optimus_lanes(self.optimus_assay_json_v4, '5.2.1')

    def test_get_optimus_inputs(self):
        lanes = input_utils.get_optimus_lanes(self.optimus_assay_json_v4, '4.6.1')
        manifest_files = dcp_utils.get_manifest_file_dicts(self.optimus_manifest_json_v4)
        r1, r2, i1 = input_utils.get_optimus_inputs(lanes, manifest_files)

        expected_r1 = ['gs://foo/L7_R1.fastq.gz', 'gs://foo/L8_R1.fastq.gz']
        expected_r2 = ['gs://foo/L7_R2.fastq.gz', 'gs://foo/L8_R2.fastq.gz']
        expected_i1 = ['gs://foo/L7_I1.fastq.gz', 'gs://foo/L8_I1.fastq.gz']

        self.assertEqual(r1, expected_r1)
        self.assertEqual(r2, expected_r2)
        self.assertEqual(i1, expected_i1)

    @staticmethod
    def data_file(file_name):
        return os.path.split(__file__)[0] + '/data/' + file_name

if __name__ == '__main__':
    unittest.main()