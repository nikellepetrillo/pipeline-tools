import os
import pytest

import pipeline_tools.shared.submission.create_file_descriptor as cfd
from pathlib import Path


@pytest.fixture(scope='module')
def test_data():
    class Data:
        file_path = '/fake/file/path.fasta'
        size = 1000
        sha256 = '12998c017066eb0d2a70b94e6ed3192985855ce390f321bbdb832022888bd251'
        crc32c = '0b83b575'
        raw_schema_url = 'http://schema.humancellatlas.org/'
        file_descriptor_schema_version = '2.0.0'
        creation_time = '2020-08-10T14:24:26.174274-07:00'

    return Data


@pytest.fixture
def data_file():
    def _data_file(file_name):
        return (
            f'{Path(os.path.split(__file__)[0]).absolute().parents[1]}/data/{file_name}'
        )

    return _data_file


class TestCreateAnalysisMetadata(object):
    def test_build_file_descriptor(self, test_data):
        file_descriptor = cfd.build_file_descriptor(
            file_path=test_data.file_path,
            size=test_data.size,
            sha256=test_data.sha256,
            crc32c=test_data.crc32c,
            raw_schema_url=test_data.raw_schema_url,
            file_descriptor_schema_version=test_data.file_descriptor_schema_version,
            creation_time=test_data.creation_time,
        )

        assert (
            file_descriptor.get('describedBy')
            == 'http://schema.humancellatlas.org/system/2.0.0/file_descriptor'
        )
        assert file_descriptor.get('schema_type') == 'file_descriptor'
        assert file_descriptor.get('content_type') == 'application/unknown'
        assert file_descriptor.get('size') == 1000
        assert (
            file_descriptor.get('sha256')
            == '12998c017066eb0d2a70b94e6ed3192985855ce390f321bbdb832022888bd251'
        )
        assert file_descriptor.get('crc32c') == '0b83b575'
        assert file_descriptor.get('file_id') == '70b63891-dc06-520d-b98a-e4df0496e68a'
        assert file_descriptor.get('file_version') == '2020-08-10T14:24:26.174274-07:00'
        assert file_descriptor.get('file_name') == 'path.fasta'