# Add this to settings.INSTALLED_APPS
SMART_ADMIN_APPS = [
    'smart_admin.apps.SmartTemplateConfig',
    'smart_admin.apps.SmartLogsConfig',
    'smart_admin.apps.SmartAuthConfig',
    'smart_admin.apps.SmartConfig',
]

SMART_ADMIN_SECTIONS = {
    'Accounting': [
        'core.Invoice',
        'core.InvoiceEntry',
    ],
    'Core': [
        'core.City',
        'core.Client',
        'core.Country',
        'core.Resource',
    ],
    'Documents': [
        'django_simple_dms',
    ],
    'Missions': [
        'core.Mission',
        'core.ExpenseCategory',
        'core.Expense',
        'core.PaymentCategory',
        'core.DocumentType',
        'core.ReimbursementCategory',
        'core.Reimbursement',
    ],
    'Projects': [
        'core.Project',
        'core.Task',
        'core.Basket',
        'core.PO',
    ],
    'Timesheets': [
        'core.SpecialLeaveReason',
        'core.TimeEntry',
        'core.TimesheetSubmission',
    ],
    '_hidden_': ['sites'],
    'Security': ['auth', 'admin.LogEntry', 'social_django', 'core.UserProfile', 'core.User', 'token_blacklist'],
    'Configuration': ['constance', 'flags', 'currencies'],
}
