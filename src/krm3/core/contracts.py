import typing
from datetime import date
from typing import Iterable

from django.utils.translation import gettext_lazy as _

if typing.TYPE_CHECKING:
    from krm3.core.models import Resource, Contract


class ContractSolver:
    """A convenience class to solve the contracts."""

    def __init__(self, resources: Iterable['Resource'] = None, resource_ids: Iterable[int] = None) -> None:
        """Initialise optionally with either resources or resource_ids."""
        if resources and resource_ids:
            raise RuntimeError(_('Cannot specify both resources and resource_ids'))

        self.cache = None
        self.resources = resources
        self.resource_ids = resource_ids

    def _populate_cache(self) -> None:
        from krm3.core.models import Contract

        qs = Contract.objects.filter(
            resource_id__in=self.resource_ids if self.resource_ids else [r.id for r in self.resources]
        )

        self.cache = {}
        for contract in qs:
            period_dict = self.cache.setdefault(contract.resource_id, {})
            period_dict[contract.period_as_tuple()] = contract

    def solve(self, resource: 'Resource | int', day: date, create_default=False) -> 'Contract | None':
        """Will solve the contract for the Resource and day."""
        from krm3.core.models import Resource

        if self.cache is None:
            self._populate_cache()
        resource_id = resource.id if isinstance(resource, Resource) else resource
        for period, contract in self.cache[resource_id].items():
            if period[0] <= day < period[1]:
                return contract
        return None
