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
- `currency`: The currency of the expense. If left blank it is resolved at runtime: the
  Mission's `default_currency`, or the base currency (`settings.BASE_CURRENCY`) when that is unset.
- `amount_base`: The amount converted to the base currency.
- `amount_reimbursement`: The amount owed for this expense, in the base currency. See [Reimbursement amount](#reimbursement-amount).
- `detail`: A short description of the expense.
- `category`: The <glossary:ExpenseCategory>.
- `document_type`: The type of document associated with the expense.
- `payment_type`: The <glossary:PaymentType>.
- `reimbursement`: The <glossary:Reimbursement> this expense is part of.
- `image`: An uploaded image of the receipt.

## Access

| Permission           | Expenses of the user's own Missions | Expenses of other Resources' Missions |
|----------------------|-------------------------------------|---------------------------------------|
| none                 | view, add, modify, delete           | no access                             |
| `view_any_expense`   | view, add, modify, delete           | view only                             |
| `manage_any_expense` | view, add, modify, delete           | view, add, modify, delete             |

## Reimbursement amount

`amount_reimbursement` tells who owes what for the expense:

- a positive value is owed by the Company to the <glossary:Resource>;
- a negative value is owed by the <glossary:Resource> to the Company;
- zero means nothing is owed.

It depends on who paid (the `personal_expense` flag of the <glossary:PaymentType>)
and on whether a receipt `image` is attached. The amount is always expressed in the
base currency (`amount_base`).

| Paid with                      | Receipt image | `amount_reimbursement` | Meaning                                                        |
|--------------------------------|---------------|------------------------|----------------------------------------------------------------|
| Personal means                 | yes           | `+amount_base`         | The Company refunds the Resource                               |
| Personal means                 | no            | `0`                    | Not refunded until a receipt is provided                       |
| Company means (e.g. CCA)       | yes           | `0`                    | Justified company spending, nothing owed                       |
| Company means (e.g. CCA)       | no            | `-amount_base`         | Unjustified company spending, the Resource must return it      |

### When it is calculated

- A newly created expense has no `amount_reimbursement` (empty).
- It is filled in, **only if still empty**, when:
    - a receipt `image` is attached to an existing expense that had none;
    - the payment type changes between personal and company;
    - the expense is included in a <glossary:Reimbursement> (admin action *Create reimbursement*).
- Admin actions on expenses not yet reimbursed:
    - *Recalculate reimbursement* recomputes the amount, overwriting the current value;
    - *Reset reimbursement* empties it, so it is recomputed later.
- Once the expense belongs to a <glossary:Reimbursement> the amount is frozen:
  attaching an image or changing the payment type is rejected, and the admin actions skip it.
