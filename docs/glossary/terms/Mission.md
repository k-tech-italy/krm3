---
description:  ""
template: term.html
terms:
  - glossary:
    - Mission
---

# Mission

_Django Model: core.Mission_

A **Mission** is a container for all the activities and expenses related to a specific work assignment or trip.

## Fields

- `status`: The current status of the mission (Draft, Submitted, Cancelled).
- `number`: The mission number.
- `title`: The title of the mission.
- `from_date`: The start date of the mission.
- `to_date`: The end date of the mission.
- `year`: The year of the mission.
- `default_currency`: The default currency for the mission.
- `project`: The Project this mission is associated with.
- `city`: The city where the mission takes place.
- `resource`: The Resource assigned to the mission.
