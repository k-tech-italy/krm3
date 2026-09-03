# # How to calculate overtime

## Overview
This document describes how overtime hours are calculated for time entries.

## Business Rules

### Untracked overtime

Overtime is always 0 if Contract.overtime is False.

### Absences and overtime

Overtime is calculated from the hours actually worked in TaskEntry records minus the Due Hours for the day.

A requested holiday or sickness is a whole-day absence and cannot coexist with task hours, so overtime is zero for those days.

Leave, special leave, and rest do not directly prevent overtime. When they coexist with task hours, overtime is still calculated from Worked Hours minus Due Hours.

### Bank Hours impact
Bank transactions are stored as a signed `DayEntry.bank` value: positive values are deposits and negative values are withdrawals. The bank value is used when validating effective hours; overtime itself is recalculated from the worked hours recorded in `TaskEntry` records minus the due hours for the day.

## Fields that generate overtime
Overtime is calculated from:

  - `day_shift_hours`
  - `night_shift_hours`
  - `travel_hours`


- leave - special-leave, rest, bank,
- holiday - whole day - exclusive, no other day or task entries - no bank too
- sick day - whole day - exclusive, no other day or task entries - no bank too

- Task hours can be recorded on a non-working day by selecting that day individually. Bulk entry skips non-working days.
- A requested holiday cannot be recorded on a public holiday.
- Without a Contract, no time entry can be recorded.
