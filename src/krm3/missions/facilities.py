from typing import TYPE_CHECKING, Dict, List, Union

from django.db.models import Max, Min
from django.forms import ValidationError

from krm3.missions.models import Expense, Reimbursement
from krm3.missions.tables import MissionExpenseTable

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from krm3.core.models import Resource


class ReimbursementFacility:
    def __init__(self, ids: Union[str, 'QuerySet']):
        if isinstance(ids, str):
            queryset = Expense.objects.filter(
                id__in=map(int, ids.split(',')))
        else:
            queryset = ids
        self.resources = {}

        self.queryset = queryset.select_related('mission', 'mission__resource')

        for expense in self.queryset:  # only submitted
            expense: Expense
            self.resources.setdefault(expense.mission.resource, {}).setdefault(expense.mission, []).append(expense)

    def render(self) -> Dict['Resource', dict]:
        """Generate the expense breakdown by resource and missions eventually rendered with tables2."""
        results = {}

        for resource, missions in self.resources.items():
            results[resource] = {mission: MissionExpenseTable(expenses, order_by=['day']) for mission, expenses in
                                 missions.items()}
        return results

    def check_year(self, year: int):
        min_max = self.queryset.aggregate(mi=Min('mission__year'), ma=Max('mission__year'))
        if not min_max['mi'] <= year <= min_max['ma']:
            raise ValidationError(f"Year must be between {min_max['mi']} and {min_max['ma']}", code='year')

    def reimburse(self, year: int, title: str) -> List[Reimbursement]:
        reimbursements = []

        for resource, missions in self.resources.items():
            tit = f'{resource}-{year}-{title}'
            reimbursement = Reimbursement.objects.create(
                title=tit, resource=resource, year=year
            )
            for mission, expenses in missions.items():
                for expense in expenses:
                    expense.calculate_reimbursement(force=False, save=True, reimbursement=reimbursement)
            reimbursements.append(reimbursement)
        return reimbursements
