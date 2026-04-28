import djclick as click

from krm3.core.models import TimeEntry, Contract, DayEntry

MAX_CONTRACT_DATE = '20501231'


def add_collections(collector):
    contract_cache = {}

    qs_contracts = Contract.objects.all()
    for contract in qs_contracts:
        upper = contract.period.upper.strftime("%Y%m%d") if contract.period.upper else MAX_CONTRACT_DATE
        contract_cache[f'{contract.resource_id}-{contract.period.lower.strftime("%Y%m%d")}-{upper}'] = contract


    for resource_id, entries in collector.items():
        entries_for_day: TimeEntry
        for day, entries_for_day in entries.items():
            obj, _ = DayEntry.get_or_create_from_entries(entries=entries_for_day)
        # resource_contract_cache = contract_cache.setdefault(resource_id, {})



@click.command()  # noqa: C901
@click.pass_context
def command(  # noqa: PLR0912, PLR0913, C901
        ctx: dict,
) -> None:


    te_qs = TimeEntry.objects.order_by('resource__last_name', 'resource__first_name', 'date')

    collector = {}
    for te in te_qs:
        res_entries = collector.setdefault(te.resource_id, {})
        day = res_entries.setdefault(te.date, [])
        day.append(te)

    add_collections(collector)
