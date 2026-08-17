---
description:  ""
template: term.html
terms:
  - glossary:
    - PO
---

# Purchase Order

_Django Model: core.PO_

A <glossary:Project>'s purchase order issued by the Customer.

## Fields

- `project`: The <glossary:Project> this PO belongs to.
- `billable`: If it is billable.
- `period`: the PO's date interval
- `state`:
