---
description:  ""
template: term.html
terms:
  - glossary:
    - Resource
---

# Resource

_Django Model: core.Resource_

A **Resource** represents an employee or a consultant working for the company.

## Fields

- `user`: The user account associated with this resource.
- `first_name`: The first name of the resource.
- `last_name`: The last name of the resource.

## Active resources

A Resource is considered active for a given date interval when at least one of its Contracts overlaps that interval.
Active resources can be retrieved with `Resource.objects.active_between(start, end)`.

This is different from `User.is_active`, which indicates whether the associated user account is enabled.
