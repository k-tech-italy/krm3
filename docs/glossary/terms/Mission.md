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

- `status`: The current status of the mission (Draft, Submitted, Cancelled). See [Lifecycle and numbering](#lifecycle-and-numbering).
- `number`: The mission number, unique within the `year`. Empty while the mission is Draft, assigned on submission.
- `title`: The title of the mission. If left blank it is generated once the mission has a number, as
  `M_<year>_<number>_<from ddMon>-<to ddMon>_<resource last name>_<city>` (e.g. `M_2024_003_02Jan-05Jan_Rossi_milano`).
- `from_date`: The start date of the mission.
- `to_date`: The end date of the mission.
- `year`: The year the mission is numbered in. If left blank it defaults to the year of `from_date`.
- `default_currency`: The default currency for the mission.
- `project`: The Project this mission is associated with.
- `city`: The city where the mission takes place.
- `resource`: The Resource assigned to the mission.

## Expense totals

The mission page shows three totals of the mission's <glossary:Expense>s, in the
<glossary:BaseCurrency> (also returned by the API as `totals`):

- *Total Refund*: the sum of the expenses' `amount_reimbursement` (positive: owed by the Company to
  the <glossary:Resource>; negative: owed by the Resource to the Company);
- *Total Anticipated*: the sum of `amount_base` of the expenses paid with company means;
- *Totals*: the mission costs, i.e. *Total Anticipated* plus the `amount_reimbursement` of the
  expenses paid with personal means.

Amounts not yet calculated (missing exchange rate or reimbursement amount) count as zero.

## Access

| Permission           | Missions of the user's own Resource | Missions of other Resources |
|----------------------|-------------------------------------|-----------------------------|
| none                 | view, modify, delete                | no access                   |
| `view_any_mission`   | view, modify, delete                | view only                   |
| `manage_any_mission` | view, modify, delete                | view, modify, delete        |

Creating a mission also requires `add_mission`.

## Lifecycle and numbering

1. A mission is created in **Draft** status by default, without a `number`
   (missions created through the API are always Draft). Creating a mission requires the
   `add_mission` permission; users without `manage_any_mission` can only create (or move)
   missions for their own <glossary:Resource>.
2. When it transitions from **Draft** to **Submitted**, the `number` is calculated and
   assigned, **only if it is still empty**. A mission can be submitted by the
   <glossary:Resource> it belongs to or by a user with the `manage_any_mission` permission,
   from the mission page (*Submit* button), the admin (*Submit* button) or the API
   (`POST /api/v1/missions/mission/<id>/submit/`). The same numbering happens when an
   administrator saves a mission as Submitted or Cancelled from the admin form.
3. The `number` is the lowest positive number not yet used by a Submitted or Cancelled
   mission of the same `year` (gaps left by deleted missions are filled first).
   Numbering is per `year`, so it restarts from 1 every new year.

### Status transitions

| From              | To        | Where                                                   | Rules                                                                                  |
|-------------------|-----------|---------------------------------------------------------|----------------------------------------------------------------------------------------|
| Draft             | Submitted | Mission page, admin *Submit* button, API, admin form    | The `number` is assigned if empty                                                      |
| Draft             | Cancelled | Admin form only                                         | The `number` is assigned if empty (Cancelled missions keep their number)               |
| Submitted         | Cancelled | Admin form only                                         | Rejected if any of its <glossary:Expense>s is already reimbursed                       |
| Cancelled         | Submitted | Admin form only                                         | The `number` is kept                                                                   |
| Submitted, Cancelled | Draft  | Admin form only                                         | The `number` must be cleared by hand; rejected if any expense is already reimbursed    |

Cancelling a mission or moving it back to Draft is not available from the mission page or
the API.

Expenses of non-Submitted missions (Draft or Cancelled) cannot be included in a
<glossary:Reimbursement>: only expenses of Submitted missions are eligible.

### Validation rules

- a Draft mission must not have a `number`; a Submitted or Cancelled mission must have one;
- the pair (`number`, `year`) is unique;
- `to_date` must not be earlier than `from_date`.

### Project of the mission

When a mission is created through the API (and so from the *Add mission* form), or its `project`
or `resource` is changed, the <glossary:Project> must be one the <glossary:Resource> is involved
in **today or later**: the resource must have a <glossary:Task> in that project whose period ends
today or later (open-ended and future tasks count). Missions created from the admin are not checked.

The *Add mission* form only lists those projects, after the resource is chosen; the resource
field is an autocomplete (search by first or last name). The list comes from
`GET /api/v1/core/project/?resource=<id>`.
