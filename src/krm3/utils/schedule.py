import datetime
from decimal import Decimal

from krm3.core.models import contracts, schedule


# XXX: this solves a circular dependency issue, but conceptually we
#      should never fall back to a default contract and always return 0
#      on dates outside all contracts
def get_default_schedule(contract: contracts.Contract, day: datetime.date) -> Decimal:
    # NOTE: this is an unsaved default schedule
    return schedule.WorkSchedule().get_hours_for_day(day)
