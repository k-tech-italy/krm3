---
description:  ""
template: term.html
terms:
  - glossary:
    - Expense
---

# Expense

_Django Model: core.Expense_

An **Expense** is the record about a single monetary transaction executed in the context of a <glossary:Mission>.


## Fields

- `mission`: The <glossary:Mission> this expense belongs to.
- `day`: The date of the expense.
- `amount_currency`: The amount in the original currency.
- `currency`: The currency of the expense.
- `amount_base`: The amount converted to the base currency.
- `amount_reimbursement`: The amount to be reimbursed.
- `detail`: A short description of the expense.
- `category`: The <glossary:ExpenseCategory>.
- `document_type`: The type of document associated with the expense.
- `payment_type`: The <glossary:PaymentType>.
- `reimbursement`: The <glossary:Reimbursement> this expense is part of.
- `image`: An uploaded image of the receipt.
