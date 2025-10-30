from enum import Enum
from typing import Any

from rich.table import Table

from krm3.timesheet.report.online import ReportCell
from krm3.timesheet.rules import Krm3Day


class Style:
    pass


class Referrable:
    def __init__(self, reference: str | None = None):
        self.ref = reference if reference is not None else hash(self)

class Stylable:
    def __init__(self, style: Style | None = None):
        self.style = style


class HtmlStyle(Style):
    pass

class ExcelStyle(Style):
    pass



class TableOrganisation(Enum):
    BY_ROWS = 'R'
    BY_COLUMNS = 'C'
    # FIXED = 'F'  # TODO


class Observer:

    def __init__(self, sensor: str):
        self.sensor = sensor


class Cell:
    def __init__(self, data: Any, reference: str | None = None, rowspan: int = 1, colspan = 1, observer:Observer = None) -> None:
        super().__init__(reference)
        self.data = data
        self.rowspan = rowspan
        self.colspan = colspan
        self.observer = observer

    def render(self):
        return self.data


class Vector:
    def __init__(self, reference: str | None = None, cells : list[Cell] = None, style: Style | None = None, hidden: bool = False) -> None:
        super().__init__(reference)
        self.cells: list[Cell] = cells or []
        self.style = style
        self.hidden = hidden

class Row(Vector):
    pass

class Column(Vector):
    pass


class CellStyle:
    pass


class Table(Referrable, Stylable):
    x: int = 0
    y: int = 0

    def __init__(self, reference: str | None = None) -> None:
        super().__init__(reference)
        self.vectors = []

    organisation: TableOrganisation = TableOrganisation.BY_ROWS

    def set_cell(self, value: object, **kwargs: dict) -> None:
        pass

    def add_cell(self, value: object, **kwargs: dict) -> None:
        self.set_cell(value=value, **kwargs)
        self._shift()

    def _shift(self) -> None:
        if self.organisation == TableOrganisation.BY_ROWS:
            self.x += 1
        elif self.organisation == TableOrganisation.BY_COLUMNS:
            self.y += 1

    def add(self, vector: Vector):
        self.vectors.append(vector)


class GreyedStyle(Style):
    pass


class HolObserver(Observer):

    def __init__(self, sensor: str):
        super().__init__(sensor)

    def handle(self, target: Cell, origin: Cell):
        origin_data: Krm3Day = origin.data
        if origin_data.is_holiday:
            target.data = 'X'
        if origin_data.is_non_working_day:
            target.style = GreyedStyle()


table = Table(reference='caminiti')

table.add(
    Row(
        reference='hol',
        style=HtmlStyle(),
        cells=[Cell(data='', colspan=2)] + [Cell(data='', observer=HolObserver(f'caminiti\.day-{i}')) for i in range(1, 31)]),
    ),
    Row(
        reference='day',

)



caminiti.column.day-4
observers=Observer(r'caminiti\.column.day-\d+', lambda obj, origin: if origin.data.is_holiday: obj.data = 'X'))