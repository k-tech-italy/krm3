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

- <glossary:ExpenseCategory>
- <glossary:PaymentType>
- Day: the transaction date
- Amount currency: the amount in the local currency
- Currency: the transaction currency (defaults to the default <glossary:Mission> currency)
- Amount base (calculated): the amount in the company <glossary:BaseCurrency>
