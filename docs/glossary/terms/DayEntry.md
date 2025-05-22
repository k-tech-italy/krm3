---
description: "Timesheet: day entry"
template: term.html
terms:
  - glossary:
    - Day Entry
---

# Day entry

A log of hours spent by a <glossary:Resource> off work on days in which they are supposed to work.

The name stems from the fact that these entries are not attached to a task, but to a calendar day.

## Classification

Day entries are classified as such:

* **Sick** day
* **Holiday**
* **Leave**: the resource has been formally allowed to leave work for a given amount of hours (i.e. is on approved leave).

## Logging day entries

To log a day entry, a resource should:

* click in the header cell with the calendar day of the absence;
* select the kind of absence in the form that appears;
* if "Leave" is selected, add the number of hours of approved leave;
* submit the form.

Clicking on an esisting day entry lets resources update it using the same form as above.

Dragging along the calendar day headers and submitting the form creates one copy of the submitted entry on each of the selected days.

Dragging an existing entry along the calendar day headers will create a copy of the dragged entry.

!!! note

    Editing the form before submitting will affect the dragged entry and all its copies.

!!! warning

    Dragging over existing entries and submitting the form will replace those entries.

!!! warning

    Logging a sick day or holiday entry will delete any existing <glossary:Task Entry> on the same day.

## Restrictions on leave hours

Logging leave hours will impose restrictions on the total amount of hours logged on the same day.

More specifically:

* When a resource is creating a new leave entry or editing an existing one:
    * If there are no task entries on the same day, the hours logged in the leave entry must not exceed the maximum daily work hours allowed for the resource.
    * Otherwise, the grand total of hours across all entries that day must not exceed the maximum daily work hours allowed for the resource.
        * If all the existing task entries on the same day equal or exceed the resource's maximum allowed daily work hours, the entry is always rejected.
* When a resource is creating anew or editing a <glossary:Task Entry> on the same day a leave entry has been logged, the grand total of hours across all entries that day must not exceed the resource's maximum allowed daily work hours.

As a rule of thumb, **no overtime is allowed on a day a resource is on leave**.
