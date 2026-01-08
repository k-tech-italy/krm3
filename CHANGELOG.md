## 2.6.0 (2026-01-08)

### Feat

- **nginx.conf**: Django app behind a nginx proxy

### Fix

- **TimeEntryAdmin**: remove search_fields since redundancy with list_filters (#207)

## 2.5.2 (2026-01-07)

### Fix

- **ci/cd-pipeline**: update GIT_BRANCH variable (#206)

## 2.5.1 (2026-01-07)

### Fix

- **ci/cd-pipeline**: add git_info file generation in pipeline
- **reports**: Show submitted schedules instead of recomputing them (#196)

## 2.5.0 (2026-01-05)

### Feat

- **fe-module**: align fe module for contacts (#205)

## 2.4.4 (2025-12-31)

### Fix

- **Reimbursement-report**: Added link to mission

## 2.4.3 (2025-12-29)

### Fix

- **Expenses**: Added Recalculate reimbursement actions

## 2.4.2 (2025-12-29)

### Fix

- **Report**: Fix 524

## 2.4.1 (2025-12-29)

### Fix

- **Report**: Fix 524 and introduces scan new QR
- **Contact**: add client fk to contact and picture to client model (#200)

## 2.4.0 (2025-12-18)

### Feat

- **Contact**: add contacts module (#195)

### Fix

- **report**: privileged users can now see all "active" resources - address missing hours data in task report
- **report**: privileged users can now see all "active" resources (#192)
- address missing hours data in task report (#199)
- **integration-tests**: update integration tests for timesheet to match FE changes (#190)

## 2.3.0 (2025-12-17)

### Feat

- **report**: show project name alongside task name in task report (#194)

### Fix

- **Task**: re-add creating tasks inline (#198)

## 2.2.8 (2025-12-12)

### Fix

- **report**: prevent crashes when accessing the report pages (#193)

## 2.2.7 (2025-12-11)

### Fix

- **templates/document_list.html**: Allow diverse chaining of filter groups in document page (#188)
- **admin.py**: delete inline task creation (#189)

## 2.2.6 (2025-12-10)

### Fix

- **sysinfo**: provide fallback for missing git_info module (#185)
- **Mission-export**: Fixed bug for image not found file

## 2.2.5 (2025-12-03)

### Fix

- **timesheet**: address API errors in the background at submission time (#181)

## 2.2.4 (2025-12-02)

### Fix

- **docker/Dockerfile**: libmagic1 dep in the final stage (#180)

## 2.2.3 (2025-12-02)

### Fix

- **docker/Dockerfile**: Fix missing libmagic1 dep (#179)

## 2.2.2 (2025-12-02)

### Fix

- **settings.py**: changelog file path as settings, added RELEASE.md (#171)
- **AvailabilityReport**: add special_leave, rest and sick hours to be… (#176)
- **TimeEntry-model**: update signal to clear bank deposit after delet… (#173)

## 2.2.1 (2025-11-28)

### Fix

- **web/views.py**: Fix wrong CHANGELOG.md path (#170)

## 2.2.0 (2025-11-28)

### Feat

- **report**: enrich timesheet submission data (#166)

### Fix

- **Dockerfile**: fix problem with changelog (#169)
- **Task**: fix clean method to allow project validation by form (#168)
- **django-adminfilters**: Updated django to 5.2.8 - fixed django-adminfilters breaking change and CVE-2025-64756 (#167)
- **django-simple-dms**: Updated django-simple-dms to 2.1.0

## 2.1.1 (2025-11-17)

### Fix

- **Profile**: Test fixes for QR code

## 2.1.0 (2025-11-17)

### Feat

- **src/krm3/web/views.py**: User Resource Form with vCard QR code (#163)

### Fix

- **Profile**: Improved qr code layout
- **i18n**: Moved compilation in stage of dockerfile

## 2.0.4 (2025-11-14)

### Fix

- **Docker**: Fix i18n

## 2.0.3 (2025-11-14)

### Fix

- **Docker**: Fixing build with i18n

## 2.0.2 (2025-11-14)

### Fix

- **i18n**: Adding message compilation to build pipeline

## 2.0.1 (2025-11-14)

### Fix

- **Report-i18n**: Fix #450 Payroll report - Label in Italian

## 2.0.0 (2025-11-11)

### Feat

- **missions/views.py**: Form to upload images or get from camera (#161)
- **TimesheetSubmission**: Fix #421 Implement persisted calculations

### Fix

- **README**: Just a fake commit to make Commitizen work!
- **Availability-report**: Fix #446 Availability report - missing all employees

## 1.13.1 (2025-11-03)

### Fix

- **TimesheetSubmission-with-the-same-resource-and-overlapping-period**: TimesheetSubmission with the same resource and overlapping period

## 1.13.0 (2025-10-31)

### Feat

- **Build-system**: Fixing build

## 1.12.1 (2025-10-31)

### Fix

- **Timesheet-report**: Aligned tests
- **Timesheet-report**: Fix #412 empty sick row when sick protocol exists (#160)
- **i18n**: Compiling messages in upgrade command

## 1.12.0 (2025-10-29)

### Feat

- **TimesheetTaskReport-AvailabilityReport**: refactor of task and av… (#157)

### Fix

- **Timesheet**: Workaround fix for #423

## 1.11.1 (2025-10-27)

### Fix

- **bs4**: bs4 needed for release api ?

## 1.11.0 (2025-10-27)

### Feat

- **TimesheetSubmission**: Introduced timesheet JSONField for persistence. Logic to be implemented

### Fix

- **Timesheet-Meal-Vouchers**: Fixed #422 threshold calcultaion with bank from

## 1.10.0 (2025-10-23)

### Feat

- configure pwa (#156)

### Fix

- **Timesheet**: Fixed Timesheet combo box sorting
- **Tests**: Fixed tests/unit/web/test_views.py::test_report_creation
- **Timesheet-Report**: Removed trave from exported payslip report

## 1.9.11 (2025-10-20)

### Fix

- **Timesheet-Report**: Report: error with permessi
- **Task**: #406 Check for orphan TimeEntries when changing Task period

## 1.9.10 (2025-10-17)

### Fix

- **krm3-fe**: Fix release.json cached in the frontend
- **Tests**: Fix for #403 TimeEntryFactory have a random date that may select a public holiday

## 1.9.9 (2025-10-16)

### Fix

- **deploy.yaml**: fix build and deploy dependencies

## 1.9.8 (2025-10-16)

### Fix

- **deploy.yaml**: changed retrive version variable value

## 1.9.7 (2025-10-16)

### Fix

- **deploy.yaml**: exported bumped out variable

## 1.9.6 (2025-10-16)

### Fix

- **deploy.yaml**: retrive fresh repo after bump

## 1.9.5 (2025-10-16)

### Fix

- **deploy.yaml**: fix cached file in deploy.yaml

## 1.9.4 (2025-10-16)

### Fix

- **deploy.yaml**: test version variable in deploy.yaml

## 1.9.3 (2025-10-16)

### Fix

- **deploy.yaml**: fix git co command with checkout command

## 1.9.2 (2025-10-16)

### Fix

- **deploy.yaml**: fix syntax in deploy.yaml
- **deploy.yaml**: fix syntax in deploy.yaml

## 1.9.1 (2025-10-16)

### Fix

- **Build-pipeline**: Moving release to manual trigger from develop

## 1.9.0 (2025-10-16)

### Feat

- **Timesheet-report**: New style export and online implemented for payslip report

### Fix

- **deploy.yaml**: fix syntax in yaml file
- **FE**: Fixed issue #321
- **deploy.yaml**: using custom cz commmit rule
- **deploy.yaml**: added configuration for specific env deploy in deploy pipeline
- **deploy.yaml**: fixed code syntax
- **deploy.yaml**: added release in deploy.yaml
- **deploy.yml**: another attempt for deploy pipeline
- **deploy.yaml**: sync develo branch fix
- **deploy.yaml**: cz commit to trigger auto bump

## 1.8.3 (2025-10-10)

### Fix

- **deploy.yaml**: cz commit to trigger auto bump

## 1.8.2 (2025-10-10)

### Fix

- **deploy.yaml**: cz commit to trigger auto bump (#147)

## 1.8.1 (2025-10-10)

### Fix

- **Report**: #363 implemented Italian i18n on the main report

## 1.8.0 (2025-10-10)

### Feat

- **deploy.yml**: Enable automatic bump upon deploy
- **Timesheet-reports**: Refactored and refreshed FE
- **Timesheet-reports**: Big refactoring of timesheet reports

### Fix

- **Pipeline-deploy-bump**: Fix Pipeline deploy bump
- **deploy-bump**: Fixing error in parsing new_version in deployment script
- **deployment-pipeline**: Trying to fix deploy pipeline
- **Tests**: Fixed tests/unit/web/test_views.py
- **Timesheet-Report**: Refactored the Excel generation of the "Payslip Report" /be/report/
- **admin.py**: set start_date mandatory for project and provide initial value in ProjectForm (#127)
- **Contract**: Fixed regression non creating default contracts
- **ContractForm-period.lower**: Issue when add a new contract

## 1.3.1 (2025-06-10)

## 1.3.0 (2025-06-10)

## 1.2.6 (2025-05-21)

## 1.7.0 (2025-10-08)

### Feat

- **Resource.preferred_in_report**: Added flag preferred_in_report to Resource
- **Contract**: Introduce Contract.meal_voucher_schedule in model (#134)

### Fix

- **Tests:test_calculate_overtime**: test_calculate_overtime expected results aligned
- **timesheets.py**: fix overtime with leave validator (#133)

### Refactor

- **test_timesheet.py**: Integration tests for readOnly EditDay modal, fix exisiting tests (#132)

### Perf

- **models/timesheets.py**: Added protocol number field, validations and related tests (#130)
- **availalibity_report.html**: use select2 in availability report (#126)

## 1.6.0 (2025-10-01)

### Feat

- **report.py**: added meal_vaucher to report (#125)
- **contracts.py**: updated contract model to include meal_vaucher, c… (#124)

### Fix

- **FE-Submodule**: Fix the Timesheet UI headers with holidays
- **TimeEntry**: updated _verify_no_overtime_with_leave_or_rest_entry not to use hardcoded hours (#128)
- **views.py**: update export_report function export resources in one sheet (#123)

### Refactor

- **src/krm3/web/views.py**: #349 report and task report visibility (#122)

### Perf

- **user_serializer.py**: module flags with label and url (#129)

## 1.5.36 (2025-09-24)

### Fix

- **timesheets.py**: update validator for deposit when schedule is 0 hours (#119)

## 1.5.35 (2025-09-18)

### Fix

- **pyproject.toml**: Ugraded Django to 5.2.6

## 1.5.34 (2025-09-18)

### Fix

- **pre-commit**: uv check moved to pre-commit
- **Makefile**: removed bump from Makefile, adjusted pre-commit yaml for cz

## 1.5.33 (2025-09-18)

### Fix

- **Makefile**: use dryrun for cz bump

## 1.5.32 (2025-09-09)

### Feat

- add commitizen setup

### Fix

- update bump command with interactive mode
