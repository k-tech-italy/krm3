---
description:  ""
template: term.html
terms:
  - glossary:
    - Reimbursement
---

# Reimbursement

_Django Model: core.Reimbursement_

A **Reimbursement** is a report document of a set of <glossary:Expense>s belonging to one or more <glossary:Mission>s.
The goal is to calculate the reimbursement owed from the <glossary:Resource> to
the Company or from Company to the <glossary:Resource>.

The amount of each <glossary:Expense> is its `amount_reimbursement`
(see [Reimbursement amount](Expense.md#reimbursement-amount)): their sum gives the
total, positive when owed to the <glossary:Resource>, negative when owed to the Company.

## Fields

- `number`: The reimbursement number, unique within the `year`.
- `year`: The fiscal year of the reimbursement.
- `month`: The month of the reimbursement (free text, by default the current month
  abbreviation, e.g. `Oct`). Reports group reimbursements by `year` and `month`.
- `title`: The title of the reimbursement, by default `R_<year>_<number>_<month>_<resource last name>`
  (e.g. `R_2025_004_Oct_Rossi`).
- `resource`: The <glossary:Resource> the reimbursement is for.
- `issue_date`: The date the reimbursement was created, set automatically.
- `paid_date`: The date the reimbursement was settled, set by hand once paid. The admin can
  filter reimbursements that are still unpaid.

The <glossary:Expense>s included in a reimbursement point to it through their
`reimbursement` field.

## How reimbursements are created

Reimbursements are created **only** from the Expense admin with the *Create reimbursement*
action:

1. Select the expenses to reimburse. All of them must be not yet reimbursed and must
   belong to a Submitted <glossary:Mission>.
2. The preview shows the selected expenses grouped by Resource and Mission. Choose the
   `year` (it must be within the years of the selected missions) and the `month`.
3. On confirmation **one Reimbursement per Resource** is created, numbered after the
   highest number already used in that `year`, with the default `title`. Each selected
   expense gets its `amount_reimbursement` calculated (if still empty) and is linked to the
   Resource's reimbursement.

Reimbursements cannot be added directly from the Reimbursement admin, not even by
superusers. Existing reimbursements can still be edited there, e.g. to set `paid_date`.

## Viewing reimbursements

- *Overview* (Reimbursement admin button): the expenses of a reimbursement with totals by
  payment type and expense category, exportable as PDF or table.
- *Reimbursement report* (Reimbursement admin action): a summary of the selected
  reimbursements by month, Resource and Mission. See
  [the reimbursement process](../../missions/index.md#reimbursement-report) for how missions
  are labelled.
