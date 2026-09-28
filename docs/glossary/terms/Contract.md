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

The contract's holiday calendar is derived from `base_in` → `City.country.country_calendar_code`. If no calendar code is available, the site default calendar is used.
