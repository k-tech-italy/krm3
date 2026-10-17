---
description:  ""
template: term.html
terms:
  - glossary:
    - PaymentType
---

# Payment Type

_Django Model: core.PaymentCategory_

A hierarchical classification of payment modality for the <glossary:Expense>s

Examples:

  - Personal (Personale)
  - Company Credit Card (CCA)
  - Wire transfer (Bonifico)

## Fields

- `title`: The name of the payment type, unique among its siblings.
- `parent`: The parent payment type, if any. Payment types form a tree and are displayed
  with their full path, e.g. `Company:CCA`.
- `active`: Whether the payment type can still be used.
- `personal_expense`: Whether the <glossary:Expense> was paid with the
  <glossary:Resource>'s own money (`True`) or with Company means such as a company credit
  card (`False`). It decides the sign of the reimbursement amount: personal expenses are
  refunded to the Resource when a receipt is attached, while Company expenses without a
  receipt must be returned by the Resource. See
  [Reimbursement amount](Expense.md#reimbursement-amount).
