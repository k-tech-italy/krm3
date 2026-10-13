import typing
from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from pyoxr import OXRError

from krm3.currencies.models import Rate
from krm3.missions.exceptions import RateConversionError

if typing.TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.http import HttpRequest

    from krm3.core.models import Expense


def update_rates(request: 'HttpRequest', qs: 'QuerySet[Expense]', force: bool = False) -> None:
    """Update the Expense amount_base for the expense not already reimbursed unless force is True."""
    if qs.filter(day__gt=datetime.today()).exists():
        messages.error(request, _('Impossible to apply rate conversions for future expenses'))
        return

    if qs.filter(reimbursement__isnull=False).exists():
        if force:
            messages.warning(request, _('Amount base recalculated'))
        else:
            messages.error(request, _('Impossible to apply rate conversions for already reimbursed expenses'))
            return

    rates_to_ensure = {}

    # Let's check all rates needed
    for expense in qs:
        if (curr := expense.get_currency_iso3()) != settings.BASE_CURRENCY:
            rates_to_ensure.setdefault(expense.day, set()).add(curr)

    rates_dict = {}
    for day, rates in rates_to_ensure.items():
        rates_dict[day] = Rate.for_date(day, include=rates)

    try:
        for expense in qs:
            curr = expense.get_currency_iso3()
            if curr == settings.BASE_CURRENCY:
                expense.amount_base = expense.amount_currency
            else:
                rate = rates_dict[expense.day]
                expense.amount_base = rate.convert(expense.amount_currency, from_currency=curr)
            expense.amount_reimbursement = expense.get_reimbursement_amount()
            expense.save()
    except OXRError as e:
        raise RateConversionError(e)
