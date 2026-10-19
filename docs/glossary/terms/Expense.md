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
- `day`: The date of the expense. It cannot be in the future.
- `amount_currency`: The amount in the original currency.
- `currency`: The currency of the expense. If left blank, it is set when the expense is saved to the
  Mission's `default_currency`, or to the base currency (`settings.BASE_CURRENCY`) when the Mission has none.
- `amount_base`: The amount converted to the <glossary:BaseCurrency>. See [Base amount](#base-amount).
- `amount_reimbursement`: The amount owed for this expense, in the base currency. See [Reimbursement amount](#reimbursement-amount).
- `detail`: A short description of the expense.
- `category`: The <glossary:ExpenseCategory>.
- `document_type`: The <glossary:DocumentType> of the document justifying the expense.
- `payment_type`: The <glossary:PaymentType> (model `core.PaymentCategory`).
- `reimbursement`: The <glossary:Reimbursement> this expense is part of.
- `image`: An uploaded image of the receipt. It is kept in private storage and served only through
  an authenticated URL, to users who can access the expense. It can also be uploaded from a phone,
  see [Receipt upload from a phone](#receipt-upload-from-a-phone).
- `created_ts`, `modified_ts`: When the expense was created and last modified, set automatically.

## Access

| Permission           | Expenses of the user's own Missions | Expenses of other Resources' Missions |
|----------------------|-------------------------------------|---------------------------------------|
| none                 | view, add, modify, delete           | no access                             |
| `view_any_expense`   | view, add, modify, delete           | view only                             |
| `manage_any_expense` | view, add, modify, delete           | view, add, modify, delete             |

## Base amount

`amount_base` is calculated when the expense is saved, if it is still empty:

- if the expense currency is the <glossary:BaseCurrency>, it equals `amount_currency`;
- otherwise `amount_currency` is converted with the exchange rate of the expense `day`. Daily
  rates are stored in the database and, when missing, fetched from Open Exchange Rates.

In the Expense admin, the *Get the rates for the dates* action calculates the missing base
amounts of the selected expenses.

## Receipt upload from a phone

The *View QR* button of an expense in the admin shows a QR code. It links to the upload page
`/missions/expense/upload/<id>/?otp=<code>`, where a phone can upload a file or a camera photo without
logging in (after logging in, the page also shows the expense details):

- the one-time code (`otp`) encodes the expense, its mission and its `modified_ts`, so it stops
  working as soon as the expense is modified, e.g. once the image has been uploaded;
- while the QR page is open it polls `GET /api/v1/missions/expense/<id>/check_ts/?ms=<millis>`
  (304 if the expense is unchanged, 204 if it was modified) and reloads the expense when the
  upload is done;
- `GET /api/v1/missions/expense/<id>/otp/` returns the current one-time code to users who can
  see the expense.

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
