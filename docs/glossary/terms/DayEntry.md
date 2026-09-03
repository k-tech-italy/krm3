---
description:  ""
template: term.html
terms:
  - glossary:
    - DayEntry
---

# DayEntry

_Django Model: core.DayEntry_

`DayEntry` records a <glossary:Resource>'s timesheet data for one day under a <glossary:Contract>. It holds day-level information and is the parent of that day's <glossary:TaskEntry> records.

Day-level fields include:

- `day`, `resource`, and `contract`: The date and the Resource and Contract the entry belongs to.
- `is_holiday`: Whether the day is a holiday according to the contract's calendar.
- `asked_holiday`: Whether the Resource requested a holiday for the day. Holiday hours are derived from the due hours; there is no `holiday_hours` field.
- `is_sick` and `protocol_number`: Whether the Resource reported sick and, when applicable, the sick certificate number.
- `leave_hours`, `special_leave_hours`, `special_leave_reason`, and `rest_hours`: Day-level leave and rest information.
- `bank`: Hours deposited to or withdrawn from the <glossary:BankOfHours>; positive values are deposits and negative values are withdrawals.
- `due_hours`, `overtime_hours`, and `meal_voucher`: The scheduled hours, calculated overtime, and meal voucher count for the day.
- `timesheet` and `closed`: The associated <glossary:TimesheetSubmission> and whether the entry is closed.
- `comment` and `last_modified`: An optional note and the last modification time.

It also stores daily totals for the related TaskEntry records in `day_hours`, `night_hours`, `travel_hours`, and `on_call_hours`.
