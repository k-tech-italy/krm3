import datetime
import typing

from psycopg.types.range import DateRange

if typing.TYPE_CHECKING:
    from krm3.utils.dates import KrmDay


type KrmDayType = KrmDay | datetime.date | str
type PeriodType = DateRange | KrmDayType
type MaybeKrmDayType = KrmDayType | None
