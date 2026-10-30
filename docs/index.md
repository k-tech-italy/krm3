---
title: Documentation
---

# Welcome to KRM3

KRM3 is the resource management platform of K-Tech and Singlewave. It covers:

- **Timesheets**: daily task hours, leaves, holidays, bank of hours and monthly submission;
- **Missions**: business trips, their expenses and the reimbursements owed to (or by) each person;
- **Contracts, projects and tasks**: who works on what, for how long and at which cost;
- **Documents, currencies and contacts**: the supporting data used by the modules above.

The application is available at <https://krm3.k-tech.it/>. Some modules are enabled per
user, so you may not see all of them.

## Where to start

| You are...                      | Start from                                                                       |
|---------------------------------|----------------------------------------------------------------------------------|
| An employee using KRM3          | The [User Guide](guides/users/index.md), then [Key Concepts](guides/users/key-concepts.md) |
| A manager or administrator      | The [Glossary](glossary/index.md) for the business rules, and the [missions and reimbursements process](missions/index.md) |
| A developer                     | The [Developer Guide](guides/developers/index.md) and the [Local development setup](guides/developers/contributing/setup.md) |

## How this documentation is organised

The sections below follow the navigation menu.

```text
Home ............................ this page
Missions ........................ the missions and reimbursements process
Examples ........................ formatting examples for documentation authors
Glossary ........................ business terms and rules, one page per term
Guide
  For Users ..................... how to use KRM3, by module
    Key Concepts                  periods and date rules shared by all modules
    Timesheet                     filling in, submitting and reporting timesheets
    Missions                      missions, expenses and reimbursements
    Availability                  who is on holiday or leave
  For Developers ................ how KRM3 is built and maintained
    Contributing                  local setup, development choices, commits
    Overtime                      how overtime is calculated
    Release                       how a version is released and deployed
    Design                        design decisions (DDR) for frontend and backend
Wiki ............................ diagrams and working notes
License ......................... the KRM3 license
Tags ............................ pages grouped by tag
```

### Missions

[The missions process](missions/index.md) explains, end to end, how a <glossary:Mission>
and its <glossary:Expense>s turn into <glossary:Reimbursement>s, and how to read the
*Reimbursement report*.

### Glossary

The [Glossary](glossary/index.md) is the **reference for the business rules**: each term
(e.g. <glossary:Contract>, <glossary:Mission>, <glossary:TimeEntry>) has its own page with
its fields, who can access it and the rules the application enforces. Wherever a term is
used in these pages it links to its glossary entry, and each glossary entry lists the pages
that mention it.

### Guide

- [For Users](guides/users/index.md): step-by-step instructions for employees, organised by
  module ([Timesheet](guides/users/timesheet/timesheet_overview.md),
  [Missions](guides/users/missions.md), [Availability](guides/users/availability.md)). Read
  [Key Concepts](guides/users/key-concepts.md) first: it explains how periods and dates are
  entered throughout the application.
- [For Developers](guides/developers/index.md): how to set up a development environment,
  the [development choices](guides/developers/contributing/develop.md),
  [commit conventions](guides/developers/contributing/commit.md), the
  [release process](guides/developers/release.md) and the
  [design decisions](guides/developers/design/key-design.md) (`DDR-*` entries) that
  changes are expected to follow.

### Examples, Wiki, Tags

- *Examples* shows the formatting blocks (notes, warnings, tags) available to documentation
  authors.
- *Wiki* collects diagrams and working material that is not (yet) part of a guide.
- *Tags* lists the pages by tag.

## Contributing to the documentation

The documentation lives in the `docs/` folder of the
[KRM3 repository](https://github.com/k-tech-italy/krm3) and is built with MkDocs: a page's
source file has the same path as its URL (e.g. `guides/users/missions/` comes from
`docs/guides/users/missions.md`), and the edit button at the top of each page opens it on
GitHub. Changes go through a pull request against `develop`.
When you change it:

- keep the [Glossary](glossary/index.md) and the code in sync: a business rule changed in
  one must be changed in the other;
- link glossary terms with `<glossary:Term>`;
- record new design decisions in `guides/developers/design/` as `DDR-<scope>-NNN` entries;
- check the build with `tox -e docs` before opening a pull request.
