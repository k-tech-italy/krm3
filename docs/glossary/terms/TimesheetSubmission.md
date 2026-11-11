---
description:  ""
template: term.html
terms:
  - glossary:
    - TimesheetSubmission
---

# TimesheetSubmission

_Django Model: core.TimesheetSubmission_

A **TimesheetSubmission** represents a <glossary:Resource>'s timesheet for a given period. It is linked to the period's <glossary:DayEntry> records; each day's <glossary:TaskEntry> records are related through their DayEntry.

While the submission is closed, its entries cannot be created, edited or deleted. A submission also cannot be created, reopened, modified or deleted while a later closed submission exists for the same resource.

To correct an earlier period, privileged users must reopen closed submissions in reverse chronological order. After making the correction, they must close them again in chronological order so that each snapshot is rebuilt from the previous authoritative balance.

## Completeness validation

A submission can be closed only when all Due Hours under an active Contract are covered. Days outside an active Contract and days with zero Due Hours do not need a DayEntry. If the submission period has no active Contract, there are no Due Hours to validate.

Each day with Due Hours must have a DayEntry, and its recorded work, holiday, sickness, leave, special leave, rest or Bank of Hours data must cover all Due Hours. A TaskEntry is needed only to record worked hours; a day fully covered by holiday, sickness or another supported absence can be complete without one. A missing DayEntry or a DayEntry with remaining hours prevents submission.

## Correcting an earlier period

For example, if both September and October are closed and September must be corrected:

1. Reopen October.
2. Reopen September.
3. Correct September's DayEntry and TaskEntry records.
4. Close September.
5. Close October.

September cannot be reopened while October remains closed.

## Submission order

The first closed submission establishes the starting point for a resource. After that, timesheets must be submitted in chronological monthly order for every month covered by an active contract. Months without an active contract are skipped, and historical gaps before the latest closed submission are ignored.

## Fields

- `period`: The date range that this timesheet covers.
- `closed`: A boolean indicating whether the timesheet is closed for editing.
- `resource`: The <glossary:Resource> to whom this timesheet belongs.
- `timesheet`: The serialized timesheet data captured when the submission is closed.
