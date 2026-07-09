import abc
import datetime
from collections.abc import Callable

import tablib

from krm3.core.models.timesheets import TimeEntryQuerySet

type Period = tuple[datetime.date, datetime.date]
type ProcessedReportData = tablib.Databook | tablib.Dataset
type Renderer[RD: ProcessedReportData, F] = Callable[[RD], F]


class ReportGenerator[RD: ProcessedReportData, **P](abc.ABC):
    """ABC for report generation flows.

    Report flows are functional-like pipelines:

    * `collect()` loads the time entries involved in the report;
    * `process()` aggregates them into a `tablib.Databook` or
      `tablib.Dataset`
    * optionally, `render()` applies a rendering callable to the
      aggregated report data to produce a representation of the latter
      in a different format.

    For convenience's sake, these flows are wrapped into a class so that
    subclasses can set up shared state between all steps.

    :param period: the focus date range for the report
    :param processed_data: the aggregated report data
    """

    def __init__(self, period: Period, *args: P.args, **kwargs: P.kwargs) -> None:
        """Automatically collect and aggregate report data.

        This is a good place to pre-fetch additional data if needed by
        both the collection and the aggregation step.

        :param period: the focus date range for the report.
        """
        self.period = period
        time_entries = self._collect(*args, **kwargs)
        self.processed_data = self._process(time_entries)

    @abc.abstractmethod
    def _collect(self, *args: P.args, **kwargs: P.kwargs) -> TimeEntryQuerySet:
        """Collect the time entries on which the report should be generated.

        :return: a Django queryset of `TimeEntry`.
        """
        ...

    @abc.abstractmethod
    def _process(self, time_entries: TimeEntryQuerySet) -> RD:
        """Aggregate the time entry data in order to form a tabular report.

        :param time_entries: the input time entries
        :return: a `tablib` databook or dataset with the processed data.
        """
        ...

    def render[F](self, renderer: Renderer[RD, F]) -> F:
        """Transform `self.processed_data` into a different format.

        :param renderer: The transformation `Callable` to apply
        :return: The result of the transformation
        """
        return renderer(self.processed_data)

    @property
    def period_start(self) -> datetime.date:
        """The start of the reporting period.

        :return: a `datetime.date`.
        """
        return self.period[0]

    @property
    def period_end(self) -> datetime.date:
        """The end of the reporting period.

        :return: a `datetime.date`.
        """
        return self.period[1]

    @property
    def dates(self) -> list[datetime.date]:
        """All the dates within the reporting period.

        Mainly used for dataset headers.

        :return: a list of `datetime.date` objects.
        """
        result = []
        current = self.period_start
        while current < self.period_end:
            result.append(current)
            current += datetime.timedelta(days=1)
        return result
