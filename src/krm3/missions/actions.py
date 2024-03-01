from django.contrib import admin, messages
from django.urls import reverse
from django.utils.safestring import mark_safe

from krm3.missions.models import Mission, Reimbursement
from krm3.utils.rates import update_rates


@admin.action(description='Create reimbursement ')
def create_reimbursement(modeladmin, request, expenses):
    if expenses.filter(mission__status=Mission.MissionStatus.DRAFT).exists():
        messages.warning(request, 'Please select only expenses of non DRAFT missions.')
        return

    if expenses.filter(reimbursement__isnull=False).exists():
        messages.warning(request, 'Please select only expenses not already reimbursed.')
        return

    try:
        msg = get_rates(modeladmin, request, expenses, silent=True)
        reimbursement = Reimbursement.objects.create(title=str(expenses.first().mission),
                                                     resource=expenses.first().mission.resource)
        counters = {
            'filled': 0,
            'p_i': 0,
            'p_noi': 0,
            'a_i': 0,
            'a_noi': 0,
        }
        for expense in expenses.all():
            expense.calculate_reimbursement(force=False, save=False)

            # Personale
            if expense.payment_type.personal_expense:
                # con immagine
                if expense.image:
                    counters['p_i'] += 1
                else:
                    counters['p_noi'] += 1
            # Aziendale
            else:
                if expense.image:
                    counters['a_i'] += 1
                else:
                    counters['a_noi'] += 1

            counters['filled'] += 1
            expense.reimbursement = reimbursement
            expense.save()

        rurl = reverse('admin:missions_reimbursement_change', args=[reimbursement.id])
        messages.success(
            request,
            mark_safe(
                msg + f' Assigned {expenses.count()}'
                      f' to new reimbursement <a href="{rurl}">{reimbursement}</a>.'
                      f" pers. con imm.={counters['p_i']}, "
                      f" pers. senza imm.={counters['p_noi']}, "
                      f" az. con imm.={counters['a_i']}, "
                      f" az. senza imm.={counters['a_noi']}")
        )
    except Exception as e:
        messages.error(request, str(e))


@admin.action(description='Get the rates for the dates')
def get_rates(modeladmin, request, queryset, silent=False):
    if queryset.filter(mission__status=Mission.MissionStatus.DRAFT).exists():
        messages.warning(request, 'Please select only expenses of non DRAFT missions.')
        return

    expenses = queryset.filter(amount_base__isnull=True)
    ret = expenses.count()
    qs = expenses.all()
    update_rates(qs)
    msg = f'Converted {ret} amounts'
    if silent:
        return msg
    else:
        messages.success(request, msg)
