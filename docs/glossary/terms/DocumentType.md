---
description:  ""
template: term.html
terms:
  - glossary:
    - DocumentType
---

# Document Type

_Django Model: core.DocumentType_

The kind of document that justifies an <glossary:Expense> (its `document_type`).

Examples:

  - Receipt (Scontrino)
  - Invoice (Fattura)
  - Other (Altro)

## Fields

- `title`: The name of the document type, unique.
- `active`: Whether the document type can still be used. Only active document types are
  returned by the API (`/api/v1/missions/document_type/`).
- `default`: Marks the default document type. It is currently not used to preselect it,
  neither in the admin nor in the frontend.
