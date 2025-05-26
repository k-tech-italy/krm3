from glob import glob
from pathlib import Path

import pytest
import yaml


def report_generate():
    files = glob(f"{Path(__file__).parent / 'test_timesheet_report'}/*.yaml")
    params = []
    for file in files:
        with open(file) as f:
            data = yaml.safe_load(f.read())
            params.append(pytest.param(data['scenario'], data['expected'], id=Path(file).stem))
    return params


@pytest.mark.parametrize("data, expected", report_generate())
def test_timesheet_report_data(data, expected):
    # do something here
    assert True
