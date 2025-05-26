import pathlib

import pytest

from testutils import yaml as test_yaml


@pytest.mark.parametrize(
    ('data', 'expected'), test_yaml.generate_parameters(pathlib.Path(__file__).parent / 'testcases/timesheet_report')
)
def test_timesheet_report_data(data, expected):
    # test logic goes here
    assert True
