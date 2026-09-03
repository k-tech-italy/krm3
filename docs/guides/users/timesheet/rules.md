# Timesheet Calculation Rules

This page consolidates all the rules used to calculate the timesheet values.
The values appear in the daily entries and in the [Timesheet Report](timesheet_report.md).

## General rules

- A Resource cannot have concurrent Contracts.
- Without a Contract a Resource cannot record any time entry.
- DayEntry.day must fall inside one Contract.period.
- TaskEntry.day_entry.day must fall inside the Task.period.
- Task hours can be recorded on a non-working day by selecting that day individually. When multiple dates are selected, non-working days are skipped.
- A requested holiday cannot be recorded on a public holiday.
- Holiday and Sick day are whole-day and exclusive: no other day or task entries are allowed for the day, including bank hours movements.

## Is Holiday

To determine if a day is a holiday for a Resource:

- The holiday calendar is derived from the Contract's base city and its Country's `country_calendar_code`, including the city's subdivision code when present. If no country calendar code is available, the site's default calendar is used.
- Sundays are considered holidays if the flag `Contract.sunday_as_holiday` is True (the default). Contracts of resources working shifts may set it to False so Sunday is treated as a regular day.

## Due Hours

In a calendar day:

- If the Resource has no Contract, OR the day is a holiday (according to the Country Calendar, not if the Resource requested a holiday for the day) then Due Hours = 0.

Else

- The Due Hours value is defined in the Resource Contract Working Schedule if it is set, else it is as per the Default Working Schedule set for the site (typically 8 hours per day, Mon-Fri).

## Worked Hours

Worked hours = _Day shift hours_ + _Night shift hours_ + _Travel hours_ recorded in the TaskEntries.

## Regular Hours

Regular hours = _Worked Hours_ - the bank movement, limited to a minimum of 0 and a maximum of _Due Hours_. Bank deposits are positive and reduce _Regular Hours_; bank withdrawals are negative and increase _Regular Hours_.

## Remaining Hours

Remaining hours = _Due Hours_ - _Regular Hours_, or 0 if _Regular Hours_ exceed the expected number of hours (_Due Hours_).

## Holiday and Sick Hours

- Holiday hours: equivalent to the expected _Due Hours_ for the day the Resource was on holiday.
- Sick hours: equivalent to the expected _Due Hours_ for the day the Resource was sick.

## Overtime

The basic value is: _Day shift hours_ + _Night shift hours_ + _Travel hours_ - _Due Hours_.
If such value is 0 or negative then _Overtime_ = 0.

Additional rules:

- Overtime is always 0 if `Contract.overtime` is False.
- Leave, special leave, rest, and bank movements do not directly affect overtime. Overtime is still calculated from Worked Hours minus Due Hours.
- A requested holiday or sickness results in zero overtime because these whole-day absences cannot coexist with task hours.

## Meal Voucher

To earn a meal voucher, the Resource must have the "meal_voucher" schedule set in the Contract. Eligible hours are _Day shift hours_, _Night shift hours_, _Travel hours_, and hours withdrawn from the Bank of Hours. A voucher is granted when eligible hours reach the threshold specified in the schedule for the day. Bank deposits and _On Call Hours_ do not count.

## Bank of Hours

The bank balance is the sum of `DayEntry.bank` for the Resource's day entries. Positive values are deposits and negative values are withdrawals, so the balance can be negative.

- Hours can be deposited to the bank when the hours worked in the day exceed the working schedule for that day.
- Hours cannot be deposited when a holiday, sick day, leave etc. is logged for the day.
- Hours can be withdrawn from the bank when the hours worked in the day are less than the working schedule for that day.
- Hours cannot be withdrawn when there are overtime hours for the day.
