import os

from krm3.config.environ import Env
def test_set_environ_for_test():

    example_variables = {
    'VAR_1': (str, 'default_1', 'develop_1'),
    'VAR_2': (str, 'default_2', 'develop_2'),
    'VAR_3': (str, 'default_3', 'develop_3'),
    }

    env = Env('KRM_3', **example_variables)

    changed_variables = {
    'VAR_1': 'changed_value_1',
    'VAR_2': 'changed_value_2'
    }

    env.set_environ_for_test(changed_variables)

    assert os.environ['VAR_1'] == 'changed_value_1'
    assert os.environ['VAR_2'] == 'changed_value_2'
    assert os.environ['VAR_3'] == 'develop_3'
