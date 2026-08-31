import datetime

from django.db.models import F, Func, Prefetch, QuerySet, Value
from ktcalendars import KTDateRange

from krm3.core.models import DayEntry, Resource, TaskEntry


def resources_in_period(
    start_date: datetime.date,
    end_date: datetime.date | None,
    tasks: bool,
    project_id: int | None,
) -> QuerySet[Resource]:
    """
    Fetch resources with contracts between two dates.

      Usage:

          for resource in resources_in_period(datetime.date(2026, 7, 1), datetime.date(2026, 7, 31)):
              for de in resource.dayentry_set.all():        # only entries in the period, no extra query
                  for te in de.taskentry_set.all():         # prefetched, .task also loaded

    Notes:
      - Open-ended period: passing (start_date, None) to period__overlap builds an unbounded-upper Postgres range,
        so it matches any contract that ends after start_date — that's your "end_date means max_date" case.
        The DayEntry filter correspondingly just drops the day__lte clause.
      - + timedelta(days=1): this follows the convention already used in this codebase
        (TimesheetSubmission.get_closed_in_period at src/krm3/core/models/timesheets.py:115) — an inclusive user-facing
         end date against the exclusive range upper bound. If your end_date is already exclusive, drop the shift.
      - distinct() is needed because a resource with two consecutive contracts both overlapping the period would
        otherwise appear twice.
      - select_related('task') on the task-entry prefetch avoids one query per task when you touch te.task; add more
        (e.g. 'task__project') if you need them.
      - When project_id is not None then task is forced True, and select_related('task') becomes
        select_related('task', 'project'). Additionally Resources are filtered for only those who have a Task in the
        period.

      One caveat: the day-entry prefetch is filtered by date only, not by "belongs to an overlapping contract" — if a
        resource has day entries in the period outside any contract you care about, add
        .filter(contract__period__overlap=period) to the day_entries queryset too.

    """
    period = (
        KTDateRange.from_start_end(start_date, end_date)
        if end_date is not None
        else KTDateRange(lower=start_date, upper=None)
    )
    day_entries = DayEntry.objects.filter(day__contained_by=period)

    if tasks or project_id:
        filters = {}
        if project_id:
            filters = {'task__project_id': project_id, 'task__period__overlap': period}
        return (
            Resource.objects.filter(contract__period__overlap=period, **filters)
            .annotate(
                _contract_range=Func(
                    F('contract__period'),
                    Value(period),
                    function='',
                    template='%(expressions)s',
                )
            )
            .distinct()
            .prefetch_related(
                Prefetch(
                    'dayentry_set',
                    queryset=day_entries.order_by('day').prefetch_related(
                        Prefetch('taskentry_set', queryset=TaskEntry.objects.select_related('task'))
                    ),
                )
            )
        )

    return (
        Resource.objects.filter(contract__period__overlap=period)
        .distinct()
        .prefetch_related(Prefetch('dayentry_set', queryset=day_entries.order_by('day')))
    )
