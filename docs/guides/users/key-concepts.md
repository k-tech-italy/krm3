# Key Concepts

## "Period" date ranges

In Krm3 several Business Objects have a "start date" and an optional "end date".
For example: Contract, PO (Purchase Order), Task, etc...

The period are stored as a "double date" rather than two separate fields.

**IMPORTANT:**
- For technical reason the "periods" are stored as "closed-open" intervals, meaning that the lower bound is included but the upper bound not.
The conventioanl notation is "[)"
This means for example that to identify 2026 February period the user must enter [2026-01-01, 2026-03-01) .
- The upper bound can optionally be left blank meaning it is an unbounbed interval (we know when the period starts but we don't know yet when it ends)

## Dates and period "compatibility"

The system should enforce the following rules:

- PO.period must be inside Project.period
- Task.period must be inside Project.period
- DayEntry.day must be inside Contract.period
- TaskEntry.day_entry.day must be inside Task.period

This imples, for example, that the system should prevent:
- accidentally shrinking a Task.period leaving "orphans" DayEntries/TaskEntries
- accidentally shrinking a Project.period leaving child Tasks with period falling outside the shrunken Project.period

and so on...
