---
description:  ""
template: term.html
terms:
  - glossary:
    - TimeEntry
---

# TimeEntry

_Django Model: core.TimeEntry_

The model recording hours for a given <glossary:Resource>, Day and (optional) Task. It is the persistent storage for <glossary:DayEntry> and Task entries


## Fields

- `date`: The date of the entry.
- `last_modified`: When the entry was last modified.
- `day_shift_hours`: Hours worked during the day.
- `sick_hours`: Hours of sick leave.
- `holiday_hours`: Hours of holiday leave.
- `leave_hours`: Hours of general leave.
- `special_leave_hours`: Hours of special leave.
- `special_leave_reason`: The reason for special leave.
- `night_shift_hours`: Hours worked during the night.
- `on_call_hours`: Hours on call.
- `travel_hours`: Hours spent traveling.
- `rest_hours`: Hours of rest.
- `comment`: A comment on the entry.
- `timesheet`: The timesheet this entry belongs to.
- `bank_to`: Hours deposited into <glossary:BankOfHours>
- `bank_from`: Hours withdrawn from <glossary:BankOfHours>
- `resource`: The <glossary:Resource> this entry belongs to
- `task`: The Task this entry is for (if any).
