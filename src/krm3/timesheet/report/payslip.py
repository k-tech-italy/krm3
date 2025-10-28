import datetime
import decimal
import typing

from .online import ReportBlock, ReportCell, ReportRow
from .base import TimesheetReport, online_timeentry_key_mapping
from krm3.utils.numbers import normal
from ...core.models import TimesheetSubmission, ExtraHoliday
from ...utils.dates import KrmDay

if typing.TYPE_CHECKING:
    from krm3.timesheet.rules import Krm3Day


class TimesheetReportOnline(TimesheetReport):
    def report_html(self) -> list[ReportBlock]:
        blocks = []
        for resource in self.resources:
            blocks.append(block := ReportBlock(resource))
            row = block.add_row(ReportRow())
            resources_report_days = self.calendars[resource.id]
            row.add_cell(sum([0 if kd.nwd else 1 for kd in resources_report_days]))
            for kd in resources_report_days:
                row.add_cell(kd)

            if any(rkd.has_data for rkd in resources_report_days):
                for key, label in online_timeentry_key_mapping.items():
                    row = block.add_row(ReportRow())
                    row.add_cell(label)
                    row.add_cell(cell_tot_hh := ReportCell(decimal.Decimal(0)))
                    for rkd in resources_report_days:
                        value = getattr(rkd, f'data_{key}')
                        row.add_cell(normal(value)).nwd = rkd.nwd
                        cell_tot_hh.value += value or decimal.Decimal(0)
                    cell_tot_hh.value = normal(cell_tot_hh.value)

                self._add_special_leaves(block)
                self._add_sick_days(block)
        return blocks

    def _add_special_leaves(self, block: ReportBlock) -> None:
        resources_report_days: list['Krm3Day'] = self.calendars[block.resource.id]
        special_leave_days: dict[str, list['Krm3Day']] = {}

        for rkd in resources_report_days:
            if rkd.data_special_leave_reason:
                special_leave_days.setdefault(rkd.data_special_leave_reason.title, []).append(rkd)

        for title, sl_days in special_leave_days.items():
            row = ReportRow()
            row.add_cell(f'Perm. speciale ({title})')
            row.add_cell(cell_tot_hh := ReportCell(decimal.Decimal(0)))
            for rkd in resources_report_days:
                value = rkd.data_special_leave_hours if rkd in sl_days else ''
                row.add_cell(normal(value)).nwd = rkd.nwd
                cell_tot_hh.value += value or decimal.Decimal(0)
            cell_tot_hh.value = normal(cell_tot_hh.value)
            block.rows.insert(len(block.rows) - 3, row)

    def _add_sick_days(self, block: ReportBlock) -> None:
        resources_report_days: list['Krm3Day'] = self.calendars[block.resource.id]
        sick_days: dict[str, list['Krm3Day']] = {}

        for rkd in resources_report_days:
            if rkd.data_sick:
                sick_days.setdefault(rkd.data_protocol_number or '', []).append(rkd)

        for title in sorted(sick_days):
            sl_days = sick_days[title]
            row = ReportRow()
            row.add_cell(f'Malattia {title}')
            row.add_cell(cell_tot_hh := ReportCell(decimal.Decimal(0)))
            for rkd in resources_report_days:
                value = rkd.data_sick if rkd in sl_days else ''
                row.add_cell(normal(value)).nwd = rkd.nwd
                cell_tot_hh.value += value or decimal.Decimal(0)
            cell_tot_hh.value = normal(cell_tot_hh.value)
            block.rows.insert(len(block.rows) - 3, row)

        if not sick_days:
            row = ReportRow()
            row.add_cell('Malattia')
            row.add_cell('0')
            for rkd in resources_report_days:
                row.add_cell('').nwd = rkd.nwd
            block.rows.insert(len(block.rows) - 3, row)

    def _load_submissions(self, from_date: datetime.date, top_period: datetime.date, resource_ids: set[int]) -> (
            dict[int, list[tuple[datetime.date, datetime.date]]] | None):
        self.submissions: dict[int, list[tuple[datetime.date, datetime.date]]] = {}
        for ts in TimesheetSubmission.objects.filter(
                resource_id__in=resource_ids, closed=True, period__overlap=(from_date, top_period)
        ):
            self.submissions.setdefault(ts.resource_id, []).append((ts.period.lower, ts.period.upper))

    def _load_extra_holidays(self) -> dict[KrmDay, list[str]] | None:
        """Retrieve the extra holidays for the given country codes."""
        short_codes = {x.split('-')[0] for x in self.country_codes}
        result = {}
        extra_holidays = list(
            ExtraHoliday.objects.filter(
                country_codes__overlap=list(self.country_codes.union(short_codes)),
                period__overlap=(self.from_date, self.to_date),
            )
        )
        for eh in extra_holidays:
            for kd in KrmDay(eh.period.lower).range_to(eh.period.upper - datetime.timedelta(days=1)):
                result.setdefault(kd, []).extend(eh.country_codes)
        return result
