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
