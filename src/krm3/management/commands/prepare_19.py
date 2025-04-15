import djclick as click
from django.db import transaction, connection


@click.command()  # noqa: C901
@click.pass_context
def command(ctx,  **kwargs):
    tables = [
        'accounting_invoiceentry',
        'accounting_invoice',
        'missions_documenttype',
        'missions_expensecategory',
        'missions_reimbursement',
        'timesheet_po',
        'timesheet_task',
        'timesheet_basket',
        'missions_mission',
        'missions_paymentcategory',
        'missions_expense',
        'timesheet_timeentry',
    ]
    with transaction.atomic():
        with connection.cursor() as cursor:
            for old_name in tables:
                new_name = old_name.split('_', 1)
                new_name = 'core_' + new_name[1]

                cursor.execute(f'ALTER TABLE IF EXISTS public.{old_name} RENAME TO {new_name}')
            cursor.execute("DELETE from public.django_migrations WHERE app in ('accounting', 'missions', 'timesheet')")
            cursor.execute("DELETE from public.django_migrations WHERE app = 'core' AND name <> '0001_initial'")
            cursor.execute("UPDATE public.django_content_type set app_label='core' WHERE app_label in ('accounting', 'missions', 'timesheet')")
