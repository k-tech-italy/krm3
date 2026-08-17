# Timesheet Calculation Rules

This page consolidates all the rules used to calculate the timesheet values.
The values appear in the daily entries and in the [Timesheet Report](timesheet_report.md).

## General rules

- A Resource cannot have concurrent Contracts.
- Without a Contract a Resource cannot record any time entry.
- DayEntry.day must fall inside one Contract.period.
- TaskEntry.day_entry.day must fall inside the Task.period.
- On non-working days the only day entry allowed is a Sick day.
- Holiday and Sick day are whole-day and exclusive: no other day or task entries are allowed for the day, including bank hours movements.

## Is Holiday

To determine if a day is a holiday for a Resource:

- The Country Calendar Code set in the Contract is used; if none is set, the default Country Calendar set for the site is used.
- Sundays are considered holidays if the flag `Contract.sunday_as_holiday` is True (the default). Contracts of resources working shifts may set it to False so Sunday is treated as a regular day.

## Due Hours

In a calendar day:

- If the Resource has no Contract, OR the day is a holiday (according to the Country Calendar, not if the Resource requested a holiday for the day) then Due Hours = 0.

Else

- The Due Hours value is defined in the Resource Contract Working Schedule if it is set, else it is as per the Default Working Schedule set for the site (typically 8 hours per day, Mon-Fri).

## Worked Hours

Worked hours = _Day shift hours_ + _Night shift hours_ + _Travel hours_ recorded in the TaskEntries.

## Regular Hours

Regular hours = _Worked hours_ + the bank daily balance, capped at the expected number of hours (_Due Hours_).

## Remaining Hours

Remaining hours = _Due Hours_ - _Worked hours_, or 0 if the Resource worked more than the expected number of hours (_Due Hours_).

## Holiday and Sick Hours

- Holiday hours: equivalent to the expected _Due Hours_ for the day the Resource was on holiday.
- Sick hours: equivalent to the expected _Due Hours_ for the day the Resource was sick.

## Overtime

The basic value is: _Day shift hours_ + _Night shift hours_ + _Travel hours_ - _Due Hours_.
If such value is 0 or negative then _Overtime_ = 0.

Additional rules:

- Overtime is always 0 if `Contract.overtime` is False.
- Overtime cannot be calculated when any of the following fields have non-zero values, as they represent time when the Resource is not performing regular work duties: `special_leave_hours`, `sick_hours`, `holiday_hours`, `leave_hours`.

## Meal Voucher

To earn a meal voucher, the Resource must have the "meal_voucher" schedule set in the Contract and must have worked in the day (_Day shift hours_ + _Night shift hours_ + _Travel hours_) at least the threshold specified in the schedule for the day.

## Bank of Hours

The bank balance is calculated by adding `bank_to` and subtracting `bank_from` for every TimeEntry of the Resource. The balance can be negative when the sum of `bank_from` exceeds the sum of `bank_to`.

- Hours can be deposited to the bank when the hours worked in the day exceed the working schedule for that day.
- Hours cannot be deposited when a holiday, sick day, leave etc. is logged for the day.
- Hours can be withdrawn from the bank when the hours worked in the day are less than the working schedule for that day.
- Hours cannot be withdrawn when there are overtime hours for the day.
