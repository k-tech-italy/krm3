---
description:  ""
template: term.html
terms:
  - glossary:
    - TimesheetSubmission
---

# TimesheetSubmission

_Django Model: core.TimesheetSubmission_

A **TimesheetSubmission** represents a <glossary:Resource>'s timesheet for a given period. It is linked to the period's <glossary:DayEntry> records; each day's <glossary:TaskEntry> records are related through their DayEntry. While the submission is closed, those entries cannot be edited or deleted. A privileged user must reopen the submission before modifying or deleting them.

## Fields

- `period`: The date range that this timesheet covers.
- `closed`: A boolean indicating whether the timesheet is closed for editing.
- `resource`: The <glossary:Resource> to whom this timesheet belongs.
- `timesheet`: The serialized timesheet data captured when the submission is closed.
