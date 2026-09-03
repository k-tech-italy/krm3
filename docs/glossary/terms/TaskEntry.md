---
description:  ""
template: term.html
terms:
  - glossary:
    - TaskEntry
---

# TaskEntry

_Django Model: core.TaskEntry_

`TaskEntry` records task-related hours for one <glossary:Task> on a particular day. It belongs to a <glossary:DayEntry>, which supplies the Resource, date, Contract, and day-level information. `TaskEntry` is one of the two concrete models covered by the generic <glossary:TimeEntry> type.

## Fields

- `task`: The Task the hours are recorded against.
- `day_entry`: The parent DayEntry for the day.
- `day_shift_hours`, `night_shift_hours`, `travel_hours`, and `on_call_hours`: Hours recorded for this Task on that day.
- `comment`: An optional note about the entry.
- `metadata`: Additional structured data associated with the entry.
