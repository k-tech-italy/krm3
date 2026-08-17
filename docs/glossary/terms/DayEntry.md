---
description:  ""
template: term.html
terms:
  - glossary:
    - DayEntry
---

# DayEntry

_Django Model: core.DayEntry_

DayEntry is the record of the Resource's activities in a day.

In contains task-agnostic data like:

- `is_holiday`: if the day is holiday according to the <glossary:Resource>'s calendar
- `is_sick`: if the <glossary:Resource> called in sick.
- `holiday_hours`: Hours of holiday leave.
- `leave_hours`: Hours of general leave.
- `special_leave_hours`: Hours of special leave.
- `special_leave_reason`: The reason for special leave.
- `last_modified`: When the entry was last modified.
- `timesheet`: The <glossary:TimesheetSubmission> this entry belongs to.
- `bank`: Hours deposited or withdrawn to/from <glossary:BankOfHours>

It also contains the summaries for the <glossary:TaskEntry> data for the day
