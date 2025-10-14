import typing

import openpyxl

from krm3.timesheet.report.base import TimesheetReport
from krm3.utils.numbers import safe_dec
from krm3.web.report_styles import (
    centered,
    header_alignment,
    header_fill,
    header_font,
    light_grey_fill,
    nwd_fill,
    thin_border,
)

report_timeentry_key_mapping = {
    'regular_hours': 'Ore ordinarie',
    'night_shift': 'Ore notturne',
    'on_call': 'Reperibilità',
    'travel': 'Viaggio',
    'holiday': 'Ferie',
    'leave': 'Permessi',
    'rest': 'Riposo',
    'overtime': 'Ore straordinarie',
    'meal_voucher': 'Buoni pasto',
}


class StreamWriter(typing.Protocol):
    def write(self, data) -> None: ...  # noqa: ANN001


class TimesheetReportExport(TimesheetReport):
    def write_excel(self, stream: StreamWriter, title: str) -> None:  # noqa: C901,PLR0912
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = title

        ws.column_dimensions['A'].width = 30

        current_row = 1

        for idx, resource in enumerate(self.resources, 1):
            # spacing between employees
            if idx > 1:
                current_row += 2

            resources_report_days = self.calendars[resource.id]

            # Header section
            headers = [
                f'{idx} - {resource.last_name.upper()} {resource.first_name}',
                '',
                *['X' if kd.holiday else '' for kd in resources_report_days],
            ]
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=current_row, column=col, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.border = thin_border
                cell.alignment = header_alignment

            current_row += 1

            # Days row
            working_days = sum([0 if kd.nwd else 1 for kd in resources_report_days])
            giorni = [
                f'Giorni {working_days}',
                'Tot HH',
                *[f'{day.day_of_week_short_i18n}\n{day.day}' for day in resources_report_days],
            ]
            for col, giorno in enumerate(giorni):
                cell = ws.cell(row=current_row, column=col + 1, value=giorno)
                cell.alignment = header_alignment
                cell.fill = header_fill
                if col > 2 and resources_report_days[col - 2].nwd:
                    cell.fill = nwd_fill

            current_row += 1

            if any(rkd.has_data for rkd in resources_report_days):
                base_mapping = report_timeentry_key_mapping

                # TODO: insert in base_mapping Permessi Speciali and Malattie

                for lnum, (key, label) in enumerate(base_mapping.items()):
                    rownum = current_row + lnum

                    cell = ws.cell(row=rownum, column=1, value=label)
                    if lnum % 2:
                        cell.fill = light_grey_fill

                    tot = None

                    for dd_num, rkd in enumerate(resources_report_days, 3):
                        value = getattr(rkd, f'data_{key}')
                        cell = ws.cell(row=rownum, column=dd_num, value=value)
                        cell.alignment = centered
                        if rkd.nwd:
                            cell.fill = nwd_fill
                        elif lnum % 2:
                            cell.fill = light_grey_fill
                        if value is not None:
                            tot = safe_dec(tot) + safe_dec(value)
                    # TOT cell
                    cell = ws.cell(row=rownum, column=2, value='' if tot is None else tot)
                    cell.alignment = centered
                    if lnum % 2:
                        cell.fill = light_grey_fill
                current_row = rownum

            else:
                ws.cell(row=current_row, column=1, value='No data available')
                current_row += 1

        wb.save(stream)
