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
- `country_calendar_code`: The country calendar code for this contract. - used for specifying country holidays
- `working_schedule`: Expected working hours for each weekday, e.g. {'mon': 8, 'tue': 8, ...}"
