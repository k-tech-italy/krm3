---
description:  ""
template: term.html
terms:
  - glossary:
    - ExtraHoliday
---

# ExtraHoliday

_Django Model: core.ExtraHoliday_

An **ExtraHoliday** represents a day or a period of days that are designated as holidays for specific countries or regions, in addition to the regular, statutory holidays. This allows for accommodating regional or company-specific non-working days.

## Fields

- `period`: The date range for which the extra holiday is applicable.
- `country_codes`: A list of country and, optionally, subdivision codes (from the `holidays` library) for which this extra holiday is valid.
- `reason`: A short description explaining the reason for the extra holiday.
