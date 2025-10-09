from datetime import datetime

from pyoxr import OXRError

from krm3.currencies.models import Rate
from krm3.missions.exceptions import RateConversionError

import typing

from krm3.utils.tools import message_add_once

if typing.TYPE_CHECKING:
    from krm3.core.models import Expense
    from django.db.models import QuerySet
    from django.http import HttpRequest


def update_rates(request: 'HttpRequest', qs: 'QuerySet[Expense]') -> None:
    rates_dict = {}
    future_days = []
    try:
        for expense in qs:
            if expense.day in rates_dict:
                rate = rates_dict[expense.day]
            elif expense.day > datetime.today().date():
                future_days.append(expense.day)
            else:
                rate = rates_dict.setdefault(expense.day, Rate.for_date(expense.day))
                expense.amount_base = rate.convert(expense.amount_currency, from_currency=expense.currency)
                if expense.amount_reimbursement is None:
                    expense.amount_reimbursement = expense.get_reimbursement_amount()
                expense.save()
    except OXRError as e:
        raise RateConversionError(e)
    if future_days:
        message = (
            f'It was impossible to apply rate conversions for the following future days:'
            f' {", ".join(map(str, set(future_days)))}'
        )
        message_add_once('warning', request, message)
