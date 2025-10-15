import typing

from krm3.core.models import Resource
from krm3.utils.numbers import normal

class UiElement:
    def __init__(self, **kwargs: dict) -> None:
        self.klass = None
        self.styles = None
        for k, v in kwargs.items():
            setattr(self, k, v)

    def render(self) -> str:
        if self.value:
            return str(self.value)
        return ''


class ReportCell(UiElement):
    def __init__(self, value: typing.Any, **kwargs: dict) -> None:
        super().__init__(**kwargs)
        self.value = value

    @property
    def negative(self) -> bool:
        """Return True if the cell value is negative."""
        return normal(self.value).startswith('-')


class ResourceCell(ReportCell):
    def render(self) -> str:
        return (
            f'{self.value["index"]} -'
            f' <strong>{self.value["resource"].last_name}</strong> {self.value["resource"].first_name}'
        )


class ReportRow(UiElement):
    def __init__(self, **kwargs: dict) -> None:
        super().__init__(**kwargs)
        self.cells: list[ReportCell] = []

    def add_cell(self, cell: ReportCell | typing.Any, **kwargs: dict) -> ReportCell:
        if not isinstance(cell, ReportCell):
            cell = ReportCell(cell, **kwargs)
        self.cells.append(cell)
        return cell


class ReportBlock(UiElement):
    def __init__(self, resource: Resource) -> None:
        super().__init__()
        self.rows: list[ReportRow] = []
        self.resource = resource

    def has_data(self) -> bool:
        return bool(len(self.rows) > 1)

    def add_row(self, row: ReportRow | None, **kwargs: dict) -> ReportRow:
        if row is None:
            row = ReportRow(**kwargs)
        self.rows.append(row)
        return row

    @property
    def width(self) -> int:
        return len(self.rows[0].cells) + 1
