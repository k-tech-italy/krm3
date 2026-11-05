---
description:  ""
template: term.html
terms:
  - glossary:
    - Contract
---

# Contract

_Django Model: core.Contract_

A **Contract** represents a formal agreement with a resource for a specific period. For one resource there cannot be overlapping Contracts

## Fields

- `resource`: The resource associated with this contract.
- `period`: The date range of the contract.
- `contract_type`: Whether the contract is for an employee, contractor, or other type of resource.
- `base_in`: The city where the resource is based. Its country's calendar code, and optional subdivision code, determine the contract's holiday calendar.
- `working_schedule`: Expected working hours for each weekday, e.g. {'mon': 8, 'tue': 8, ...}"
- `holiday_day`: The day of the week that is always a holiday for the contract, even when it is a weekend day.
  Defaults to Sunday; empty means no weekly holiday (e.g. for resources working shifts).
- `version`: The record revision (django-concurrency), changed on every save. It detects changes made to the
  Contract while someone is editing or terminating it.

The contract's holiday calendar is derived from `base_in` → `City.country.country_calendar_code`. If no calendar code is available, the site default calendar is used. The `holiday_day` and the
<glossary:ExtraHoliday> days are added to it.

## Termination

An open-ended Contract is ended with the *Terminate* button of the Contract admin, which requires the
`core.change_contract` permission. The termination date is the last day of the Contract and cannot precede its
start. Before anything is changed, a confirmation page lists what the termination does to the resource's data
after that date:

- the <glossary:DayEntry> records after the termination date are deleted, with their <glossary:TaskEntry> records,
  including those of submitted timesheets;
- the <glossary:Task> records starting after the termination date are deleted;
- the Tasks starting on or before the termination date and ending after it (or never) are truncated to end on it;
- the <glossary:TimesheetSubmission> records starting after the termination date are deleted; the one spanning it is
  truncated to end on it and, when closed, its snapshot is rebuilt without the deleted days.

The Contract `version` is read when the *Terminate* button is pressed and carried through the confirmation pages.
On the final confirmation the Contract row is locked (`SELECT ... FOR UPDATE`) only if it still has that version,
and all the changes above are made in the same transaction. If the Contract was changed in the meantime, nothing is
changed and the termination has to be started again.
