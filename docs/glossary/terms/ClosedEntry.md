---
description:  ""
template: term.html
terms:
  - glossary:
    - ClosedEntry
---

# ClosedEntry

A closed entry is a <glossary:DayEntry> or <glossary:TaskEntry> linked to a closed <glossary:TimesheetSubmission>. A TaskEntry inherits this state through its DayEntry.

Closed entries cannot be created, edited or deleted. A privileged user may reopen their submission only when no later closed submission exists for the same resource. To correct an earlier period, later submissions must first be reopened in reverse chronological order.
