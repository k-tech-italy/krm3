import logging

from django.shortcuts import redirect
from django.views.generic.base import View

from krm3.missions.actions import create_reimbursement
from krm3.missions.models import Expense

logger = logging.getLogger(__name__)


class ReimburseMissionsView(View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        to_reimburse = request.session['to-reimburse']
        back = request.session['back']
        del request.session['to-reimburse']
        del request.session['back']

        for r, expense_ids in to_reimburse.items():
            expenses = Expense.objects.filter(id__in=expense_ids)
            create_reimbursement(None, request, expenses)

        return redirect(back)
