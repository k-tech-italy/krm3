# # How to calculate overtime

## Overview
This document describes how overtime hours are calculated for time entries.

## Business Rules
### Fields that prevent overtime
Overtime cannot be calculated when any of the following fields have non-zero values:

  - `special_leave_hours`
  - `sick_hours`
  - `holiday_hours`
  - `leave_hours`

These fields represent time when the employee is not performing regular work duties. Overtime can only be calculated
for actual working hours.

### Bank Hours impact
The time bank system(`bank_from` and `bank_to`) affects overtime calculation:

## Fields that generate overtime
When special activity fields are all zero, overtime is calculated based on:

  - `day_shift_hours`
  - `night_shift_hours`
  - `travel_hours`


- leave - special-leave, rest, bank,
- holiday - whole day - exclusive, no other day or task entries - no bank too
- sick day - whole day - exclusive, no other day or task entries - no bank too

- day entries in non working days i can only have sick day
- day entries without non working days can have every day entry
- without contract i cannot put any time entry
