---
description:  ""
template: term.html
terms:
  - glossary:
    - TaskEntry
---

# TaskEntry

_Django Model: core.TimeEntry_

TaskEntry is a <glossary:TimeEntry> with a specified Task and it represents work on a particular task (e.g., shift, travel, on-call duty).

### TaskEntry may include:
- day shift hours
- night shift hours
- travel hours
- on call hours

### TaskEntry **cannot** include:
- holiday hours
- sick hours
- leave hours (general time off)
- special leave hours (time off with a specified reason)
- rest hours
(These hours belong to a <glossary:DayEntry>.)
