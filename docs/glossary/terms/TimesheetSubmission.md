---
description:  ""
template: term.html
terms:
  - glossary:
    - TimesheetSubmission
---

# TimesheetSubmission

_Django Model: core.TimesheetSubmission_

A **TimesheetSubmission** represents a block of <glossary:TimeEntry> records for a specific <glossary:Resource> over a given period, submitted for approval or processing. Once a timesheet is closed, the entries within it are considered final and can be edited and/or deleted only by privileged users.

## Fields

- `period`: The date range that this timesheet covers.
- `closed`: A boolean indicating whether the timesheet is closed for editing.
- `resource`: The <glossary:Resource> to whom this timesheet belongs.
