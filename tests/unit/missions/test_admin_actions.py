"""Every action declared by the missions admins must exist (#687)."""

import pytest
from django.contrib import admin

from krm3.core.models import Expense, Mission, Reimbursement


@pytest.mark.parametrize(
    'model',
    [
        pytest.param(Mission, id='mission'),
        pytest.param(Expense, id='expense'),
        pytest.param(Reimbursement, id='reimbursement'),
    ],
)
def test_declared_actions_exist(model):
    model_admin = admin.site._registry[model]

    missing = [action for action in model_admin.actions if model_admin.get_action(action) is None]

    assert missing == []


def test_mission_actions(rf, admin_user):
    request = rf.get('/')
    request.user = admin_user

    actions = admin.site._registry[Mission].get_actions(request)

    assert 'export' in actions
    assert 'reimburse' not in actions
