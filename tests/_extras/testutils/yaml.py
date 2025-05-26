import pathlib
from typing import Iterator

from _pytest.mark import ParameterSet
import pytest
import yaml


class NoScenarioFilesFound(Exception):
    def __init__(self, path: str | pathlib.Path) -> None:
        self.path = pathlib.Path(path)

    def __str__(self) -> str:
        return f'No test cases found at {self.path}'


def generate_parameters(test_case_dir: str | pathlib.Path) -> Iterator[ParameterSet]:
    """Generate parameter sets for parametric lists from YAML scenario files.

    Given the path to a directory containing scenario files, this function
    lazily generates `pytest` parameter sets, one for each YAML file
    contained in that directory.

    Each parameter sets contains the initial scenario data under "scenario"
    and the expected data under "expected", and its id is the name of the
    scenario file without the `.yaml` extension.

    See `tests/unit/timesheet/testcases/timesheet_report/scenario.yaml.sample`
    for an example of a scenario file.

    :param test_case_dir: The path to the directory containing the
        scenario files
    :raises NoScenarioFilesFound: No YAML files have been found.
    :raises KeyError: The file does not include a "scenario" or "expected"
        section.
    :return: An iterator of Pytest parameter sets.
    """
    files = pathlib.Path(test_case_dir).glob('*.yaml')
    did_yield = False

    for file in files:
        with file.open() as fd:
            data = yaml.safe_load(fd.read())
            yield pytest.param(data['scenario'], data['expected'], id=file.stem)
            did_yield = True

    if not did_yield:
        raise NoScenarioFilesFound(test_case_dir)
