import abc
from collections.abc import Callable
import datetime

import tablib

from krm3.core.models.timesheets import TimeEntryQuerySet

type Period = tuple[datetime.date, datetime.date]
type ProcessedReportData = tablib.Databook | tablib.Dataset
type Renderer[RD: ProcessedReportData, F] = Callable[[RD], F]


class ReportGenerator[RD: ProcessedReportData, **P](abc.ABC):
    def __init__(self, period: Period, *args: P.args, **kwargs: P.kwargs) -> None:
        self.period = period
        time_entries = self.collect(*args, **kwargs)
        self.processed_data = self.process(time_entries)

    @abc.abstractmethod
    def collect(self, *args: P.args, **kwargs: P.kwargs) -> TimeEntryQuerySet:
        """Collect the time entries on which the report should be generated.

        :return: a Django queryset of `TimeEntry`.
        """
        ...

    @abc.abstractmethod
    def process(self, time_entries: TimeEntryQuerySet) -> RD:
        """Aggregate the time entry data in order to form a tabular report.

        :param time_entries: the input time entries
        :return: a `tablib` databook or dataset with the processed data.
        """
        ...

    def render[F](self, renderer: Renderer[RD, F]) -> F:
        """Transform `self.report_data` into a human-readable format.

        :param renderer: The transformation `Callable` to apply
        :return: The result of the transformation
        """
        return renderer(self.processed_data)

    @property
    def start(self) -> datetime.date:
        """The start of the reporting period.

        :return: a `datetime.date`.
        """
        return self.period[0]

    @property
    def end(self) -> datetime.date:
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
        current = self.start
        while current < self.end:
            result.append(current)
            current += datetime.timedelta(days=1)
        return result
