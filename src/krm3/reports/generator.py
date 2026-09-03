from __future__ import annotations

import abc
import datetime
from typing import TYPE_CHECKING, Callable

import tablib

if TYPE_CHECKING:
    from collections.abc import Iterator

type Period = tuple[datetime.date, datetime.date]
type ProcessedReportData = tablib.Databook | tablib.Dataset
type Renderer[RD: ProcessedReportData, F] = Callable[[RD], F]


class ReportGenerator[RawReportData, RD: ProcessedReportData, **P](abc.ABC):
    """ABC for report generation flows.

    Report flows are functional-style pipelines in three steps:
    * data collection: loads the time entries involved in the report;
    * data processing: aggregates the data from the collected time
        entries into a `tablib.Databook` or a `tablib.Dataset`;
    * rendering: apply a callable to the aggregated report data to
        produce a representation of the latter in a different format.
        This step is _optional_.

    This class wraps the pipeline so that subclasses can set up shared
    state for all steps.

    :param period: the focus date range for the report (inclusive at
        the start, exclusive at the end).
    :param processed_data: the aggregated report data.
    """

    def __init__(self, period: Period, *args: P.args, **kwargs: P.kwargs) -> None:
        """Automatically collect and aggregate report data.

        This is a good place to pre-fetch additional data as shared
        state across generation steps.

        :param period: the focus date range for the report.
        """
        self.period = period
        self.period_start, self.period_end = period
        raw_data = self._collect(*args, **kwargs)
        self.processed_data = self._process(raw_data)

    @abc.abstractmethod
    def _collect(self, *args: P.args, **kwargs: P.kwargs) -> RawReportData:
        """Collect the raw data with which the report should be generated.

        :return: the raw data to process.
        """
        ...

    @abc.abstractmethod
    def _process(self, raw_data: RawReportData) -> RD:
        """Aggregate the raw data in order to form a tabular report.

        :param raw_data: the raw data collected in `_collect()`.
        :return: a `tablib` databook or dataset with the processed data.
        """
        ...

    def render[F](self, renderer: Renderer[RD, F]) -> F:
        """Convert the processed report data to a different format.

        :param renderer: the transformation `Callable` to apply.
        :return: the transformed data.
        """
        return renderer(self.processed_data)

    def dates(self) -> Iterator[datetime.date]:
        """Iterate over all the dates within the reporting period.

        Mainly for dataset headers.

        :return: an iterator of `datetime.date`s from the start to the
            end of the period.
        """
        current = self.period_start
        while current < self.period_end:
            yield current
            current += datetime.timedelta(days=1)
