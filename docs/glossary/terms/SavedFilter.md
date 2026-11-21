---
description:  ""
template: term.html
terms:
  - glossary:
    - SavedFilter
---

# SavedFilter

_Django Model: core.SavedFilter_

A **SavedFilter** is a set of filter values that a user saved with a name, with *Save as* in the filter
of a page or table of the frontend (e.g. the missions or the expenses list), to apply it again later.

## Rules

- Saved filters are personal: each user sees, applies and deletes only their own, superusers included.
- The name is unique per user and page: saving with the name of an existing filter of the same page
  replaces it.
- A user can mark one filter per page as *default*: it is applied when the page or table is loaded
  without filters. Saving a default filter makes it the only default of its page.
- The *Filters* tab of the user profile lists the saved filters grouped by page; from there they can be
  opened (when the frontend address was saved) or deleted.

## Fields

- `user`: the owner.
- `page`: the page or table the filter applies to, e.g. `missions`, `expenses`.
- `name`: the name chosen by the user.
- `values`: the filter values, one entry per filter field (a string or a list of strings).
- `summary`: the filter as people read it, with field and option labels, shown in the profile.
- `url`: the frontend address that opens the page with this filter applied.
- `is_default`: whether the filter is applied when the page is loaded without filters.
