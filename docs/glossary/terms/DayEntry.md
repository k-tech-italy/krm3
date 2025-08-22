---
description:  ""
template: term.html
terms:
  - glossary:
    - DayEntry
---

# DayEntry

_Django Model: core.TimeEntry_

DayEntry is <glossary:TimeEntry> without specified Task and it's affecting all day (ie. Holiday, Sick day, Leave...).
### DayEntry may include:
- holiday hours
- sick hours
- leave hours (general time off)
- special leave hours (time off with a specified reason)
- rest hours
- bank to hours
- bank from hours
### DayEntry **cannot** include:
- day shift hours
- night shift hours
- travel hours
- on call hours
(These hours belong to a <glossary:TaskEntry>.)
