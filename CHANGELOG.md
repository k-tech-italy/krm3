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
