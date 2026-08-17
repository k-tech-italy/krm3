---
description:  ""
template: term.html
terms:
  - glossary:
    - Task
---

# Task

_Django Model: core.Task_

Is an activity to be performed by a <glossary:Resource> related to a <glossary:Project>

### Task fields:

- `title`
- `basket` (optional): the <glossary:Basket> to be "consumed"
- `period`: the activity's date interval
- `work_price`: the regular time cost to the customer
- `on_call_price`: the cost to the customer when the <glossary:Resource> is on call
- `travel_price`: the cost to the customer when the <glossary:Resource> is travelling
- `overtime_price`: the cost to the customer when the <glossary:Resource> works overtime
- `color`: the color to be used in the frontend
