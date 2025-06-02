from __future__ import annotations

import pydantic


class Hours(pydantic.BaseModel):
    day_shift: float
    sick: float = 0.0
    holiday: float = 0.0
    leave: float = 0.0
    special_leave: float = 0.0
    night_shift: float = 0.0
    on_call: float = 0.0
    travel: float = 0.0
    rest: float = 0.0
    special_leave_reason_id: int | None = None
