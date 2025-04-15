import datetime
import typing

from django.contrib import admin, messages
from django.template.response import TemplateResponse

from krm3.missions.facilities import ReimbursementFacility
from krm3.missions.forms import MissionsReimbursementForm
from krm3.core.models import Mission
from krm3.sentry import capture_exception
from krm3.utils.rates import update_rates

if typing.TYPE_CHECKING:
    from django.db.models import QuerySet

    from krm3.core.models import Expense


@admin.action(description='Create reimbursement ')
def create_reimbursement(modeladmin, request, expenses: typing.Union['QuerySet', typing.List['Expense']]):
    if expenses.filter(mission__status=Mission.MissionStatus.DRAFT).exists():
        messages.warning(request, 'Please select only expenses of SUBMITTED missions.')
        return

    if expenses.filter(reimbursement__isnull=False).exists():
        messages.warning(request, 'Please select only expenses not already reimbursed.')
        return

    try:
        _ = get_rates(modeladmin, request, expenses, silent=True)

        form = MissionsReimbursementForm(initial={
            'expenses': ','.join([str(pk) for pk in expenses.values_list('id', flat=True)]),
        })
        return TemplateResponse(
            request,
            'admin/missions/reimbursement/preview.html',
            {'form': form, 'resources': ReimbursementFacility(expenses).render()}
        )

    except Exception as e:
        capture_exception(e)
        messages.error(request, str(e))


@admin.action(description='Get the rates for the dates')
def get_rates(modeladmin, request, queryset, silent=False):
    if queryset.filter(mission__status=Mission.MissionStatus.DRAFT).exists():
        messages.warning(request, 'Please select only expenses of SUBMITTED missions.')
        return

    expenses = queryset.filter(amount_base__isnull=True)
    ret = expenses.count()
    qs = expenses.all()
    update_rates(qs)
    msg = f'Converted {ret} amounts'
    if silent:
        return msg
    else:
        messages.success(request, msg)
