import decimal
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

import cv2
import django_tables2 as tables
from admin_extra_buttons.decorators import button
from admin_extra_buttons.mixins import ExtraButtonsMixin
from adminfilters.autocomplete import AutoCompleteFilter
from adminfilters.dates import DateRangeFilter
from adminfilters.mixin import AdminFiltersMixin
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin import ModelAdmin
from django.contrib.admin.sites import site
from django.http.response import FileResponse, HttpResponseRedirect
from django.shortcuts import redirect, reverse
from django.template.response import TemplateResponse
from django.utils.html import format_html
from django.utils.http import urlencode
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from mptt.admin import MPTTModelAdmin
from rest_framework.reverse import reverse as rest_reverse

from krm3.currencies.models import Currency
from krm3.missions.forms import ExpenseAdminForm, MissionAdminForm, MissionsImportForm
from krm3.missions.impexp.export import MissionExporter
from krm3.missions.impexp.imp import MissionImporter
from krm3.missions.models import DocumentType, Expense, ExpenseCategory, Mission, PaymentCategory, Reimbursement
from krm3.missions.session import EXPENSE_UPLOAD_IMAGES
from krm3.missions.transform import clean_image, rotate_90
from krm3.styles.buttons import DANGEROUS, NORMAL
from krm3.utils.queryset import ACLMixin
from krm3.utils.rates import update_rates


class ExpenseInline(admin.TabularInline):  # noqa: D101
    form = ExpenseAdminForm
    model = Expense
    extra = 3
    exclude = ['amount_base', 'amount_reimbursement', 'reimbursement', 'created_ts', 'modified_ts']

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'currency':
            kwargs['queryset'] = Currency.objects.actives()
        return super(ExpenseInline, self).formfield_for_foreignkey(db_field, request, **kwargs)


@admin.action(description='Export selected missions')
def export(modeladmin, request, queryset):
    pathname = MissionExporter(queryset).export()
    response = FileResponse(open(pathname, 'rb'))
    return response


class ExpenseTable(tables.Table):
    attachment = tables.Column(empty_values=())

    def render_amount_currency(self, record):

        if record.payment_type.personal_expense:
            value = f'<span style="color: blue;">{record.amount_currency} {record.currency.iso3}</span>'
        else:
            value = f'{record.amount_currency} {record.currency.iso3}'
        return mark_safe(value)

    def render_amount_base(self, value):
        if value and value < decimal.Decimal(0):
            return mark_safe('<span style="color: red;">%s</span>' % value)
        return value

    def render_amount_reimbursement(self, value):
        if value and value < decimal.Decimal(0):
            return mark_safe('<span style="color: red;">%s</span>' % value)
        return value

    def render_day(self, value):
        return datetime.strftime(value, '%Y-%m-%d')

    def render_id(self, value):
        url = reverse('admin:missions_expense_change', args=[value])
        return mark_safe(f'<a href="{url}">{value}</a>')

    def render_image(self, value):
        file_type = value.name.split('.')[-1]
        # url = reverse('admin:missions_expense_change', args=[value])
        return mark_safe(f'<a href="{value.url}">{file_type}</a>')

    def render_attachment(self, record):
        if record.image:
            return self.render_image(record.image)
        else:
            url = reverse('admin:missions_expense_changelist')
            return mark_safe(f'<a href="{url}{record.id}/view_qr/">--</a>')

    def render_reimbursement(self, record):
        if record.reimbursement:
            url = reverse('admin:missions_reimbursement_change', args=[record.reimbursement.id])
            return mark_safe(f'<a href="{url}">{record.reimbursement}</a>')
        else:
            return '--'

    class Meta:
        model = Expense
        exclude = ('mission', 'created_ts', 'modified_ts', 'image', 'currency')


@admin.register(Mission)
class MissionAdmin(ACLMixin, ExtraButtonsMixin, AdminFiltersMixin, ModelAdmin):
    form = MissionAdminForm
    autocomplete_fields = ['project', 'city', 'resource']
    actions = [export]
    search_fields = ['resource__first_name', 'resource__last_name', 'title', 'project__name', 'city__name', 'number']

    inlines = [ExpenseInline]
    list_display = ('number', 'year', 'resource', 'project', 'title', 'from_date', 'to_date',
                    'default_currency', 'city')
    list_filter = (
        ('resource', AutoCompleteFilter),
        ('project', AutoCompleteFilter),
        ('city', AutoCompleteFilter),
        ('from_date', DateRangeFilter),
        ('to_date', DateRangeFilter),
    )

    fieldsets = [
        (
            None,
            {
                'fields': [
                    ('number', 'year', 'title'),
                    ('from_date', 'to_date', 'default_currency'),
                    ('project', 'city', 'resource'),
                ]
            }
        )
    ]

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'default_currency':
            kwargs['queryset'] = Currency.objects.actives()
        return super(MissionAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    @button(
        html_attrs=NORMAL,
    )
    def add_expense(self, request, pk):
        mission = Mission.objects.get(pk=pk)
        from_date = mission.from_date.strftime('%Y-%m-%d')
        return redirect(reverse('admin:missions_expense_add') + f'?mission_id={pk}&day={from_date}')

    @button(html_attrs=NORMAL)
    def import_missions(self, request):  # noqa: D102
        if request.method == 'POST':
            form = MissionsImportForm(request.POST, request.FILES)
            if form.is_valid():
                target = MissionImporter(request.FILES['file']).store()
                data = MissionImporter.get_data(target)

                data = json.dumps(data, indent=4)

                return TemplateResponse(
                    request,
                    context={'data': data}, template='admin/missions/mission/import_missions_check.html'
                )
        else:
            form = MissionsImportForm()
            return TemplateResponse(
                request,
                context={'form': form}, template='admin/missions/mission/import_missions.html'
            )

    @button(
        html_attrs=NORMAL,
    )
    def overview(self, request, pk):
        mission = self.get_object(request, pk)

        qs = mission.expenses.all()
        update_rates(qs)

        expenses = ExpenseTable(qs, order_by=['day'])

        summary = {
            'Spese trasferta': decimal.Decimal(0.0),
            'Anticipato': decimal.Decimal(0.0),
            'Da rimborsare': decimal.Decimal(0.0)}
        for expense in qs:
            summary['Spese trasferta'] += expense.amount_base or decimal.Decimal(0.0)
            summary['Anticipato'] += expense.amount_base if expense.payment_type.personal_expense is False\
                else decimal.Decimal(0.0)
            summary['Da rimborsare'] += expense.amount_reimbursement or decimal.Decimal(0.0)

        return TemplateResponse(
            request,
            context={
                'site_header': site.site_header,
                'mission': mission,
                'expenses': expenses,
                'summary': summary,
                'base': settings.CURRENCY_BASE,
                'filename': format_html(f'{slugify(str(mission))}.pdf')
            },
            template='admin/missions/mission/summary.html')

    @button(
        html_attrs=NORMAL,
        visible=lambda btn: bool(btn.original.id)
    )
    def view_expenses(self, request, pk):
        url = reverse('admin:missions_expense_changelist') + f'?mission_id={pk}'
        return HttpResponseRedirect(url)


@admin.register(DocumentType)
class DocumentTypeAdmin(ModelAdmin):
    list_display = ['title', 'active', 'default']
    search_fields = ['title']


@admin.register(PaymentCategory)
class PaymentCategoryAdmin(MPTTModelAdmin):
    list_display = ['title', 'active', 'personal_expense']
    search_fields = ['title']
    autocomplete_fields = ['parent']
    list_filter = ['personal_expense']


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(MPTTModelAdmin):
    list_display = ['title', 'active']
    search_fields = ['title']
    autocomplete_fields = ['parent']


@admin.action(description='Get the rates for the dates')
def get_rates(modeladmin, request, queryset):
    expenses = queryset.filter(amount_base__isnull=True)
    ret = expenses.count()
    qs = expenses.all()
    update_rates(qs)
    messages.success(request, f'Converted {ret} amounts')


@admin.action(description='Create reimbursement ')
def create_reimbursement(modeladmin, request, queryset):
    qs = queryset
    expenses = queryset.filter(reimbursement__isnull=True)
    count = expenses.count()

    if count == 0:
        messages.info(request, 'No expenses needing reimbursement found')
        return

    reimbursement = Reimbursement.objects.create(title=str(qs.first().mission))
    counters = {
        'filled': 0,
        'p_i': 0,
        'p_noi': 0,
        'a_i': 0,
        'a_noi': 0,
    }
    for expense in expenses.all():
        expense.reimbursement = reimbursement

        if expense.amount_reimbursement is None:
            counters['filled'] += 1

            # Personale
            if expense.payment_type.personal_expense:
                # con immagine
                if expense.image:
                    expense.amount_reimbursement = expense.amount_base
                    counters['p_i'] += 1
                else:
                    expense.amount_reimbursement = 0
                    counters['p_noi'] += 1
            # Aziendale
            else:
                if expense.image:
                    expense.amount_reimbursement = 0
                    counters['a_i'] += 1
                else:
                    expense.amount_reimbursement = decimal.Decimal(-1) * expense.amount_base
                    counters['a_noi'] += 1
        expense.save()

    messages.success(
        request,
        f'Out of {qs.count()} selected, we assigned {count}'
        f' to new reimbursement {reimbursement} ({reimbursement.id}).'
        f" pers. con imm.={counters['p_i']}, "
        f" pers. senza imm.={counters['p_noi']}, "
        f" az. con imm.={counters['a_i']}, "
        f" az. senza imm.={counters['a_noi']}, "
    )


@admin.register(Expense)
class ExpenseAdmin(ACLMixin, ExtraButtonsMixin, AdminFiltersMixin, ModelAdmin):
    readonly_fields = ['amount_base']
    form = ExpenseAdminForm
    autocomplete_fields = ['mission', 'missions__title', 'currency', 'category', 'payment_type']
    list_display = ('mission', 'day', 'colored_amount_currency',  'colored_amount_base', 'colored_amount_reimbursement',
                    'category', 'document_type', 'payment_type', 'link_to_reimbursement', 'image')
    list_filter = (
        ('mission__resource', AutoCompleteFilter),
        ('mission', AutoCompleteFilter),
        ('category', AutoCompleteFilter),
        'mission__number',
    )
    search_fields = ['amount_currency']
    fieldsets = [
        (
            None,
            {
                'fields': [
                    ('mission', 'day'),
                    ('amount_currency', 'currency'),
                    ('amount_base', 'amount_reimbursement'),
                    'detail',
                    ('category', 'payment_type', 'reimbursement'),
                    'image']
            }
        )
    ]
    actions = [get_rates, create_reimbursement]

    def colored_amount_currency(self, obj):
        if obj.payment_type.personal_expense:
            cell_html = '<span style="color: blue;">%s</span>'
        else:
            cell_html = '%s'
        # for below line, you may consider using 'format_html', instead of python's string formatting
        return format_html(cell_html % f'{obj.amount_currency} {obj.currency.iso3}')
    colored_amount_currency.short_description = 'Amount currency'

    def colored_amount_reimbursement(self, obj):
        value = obj.amount_base
        if obj.amount_reimbursement and obj.amount_reimbursement < decimal.Decimal(0):
            cell_html = '<span style="color: red;">%s</span>'
            value *= decimal.Decimal(-1)
        else:
            cell_html = '%s'

        # for below line, you may consider using 'format_html', instead of python's string formatting
        return format_html(cell_html % value)
    colored_amount_reimbursement.short_description = 'Amount reimbursement'

    def colored_amount_base(self, obj):
        if obj.amount_base < decimal.Decimal(0):
            cell_html = '<span style="color: red;">%s</span>'
        else:
            cell_html = '%s'
        # for below line, you may consider using 'format_html', instead of python's string formatting
        return format_html(cell_html % obj.amount_base)
    colored_amount_base.short_description = 'Amount base'

    def link_to_reimbursement(self, obj):
        if obj.reimbursement:
            link = reverse('admin:missions_reimbursement_change', args=[obj.reimbursement.id])
            return format_html('<a href="{}">{}</a>', link, obj.reimbursement)
        else:
            return '--'
    link_to_reimbursement.short_description = 'Reimbursement'
    # link_to_reimbursement.allow_tags = True

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'currency':
            kwargs['queryset'] = Currency.objects.actives()
        return super(ExpenseAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    def get_form(self, request, obj=None, change=False, **kwargs):
        if obj and (revert := request.GET.get('revert')):
            shutil.copy(revert, obj.image.file.name)
        return super().get_form(request, obj, change, **kwargs)

    def get_changeform_initial_data(self, request):
        ret = super().get_changeform_initial_data(request)
        pk = ret.pop('mission_id', None)
        if pk:
            ret['mission'] = Mission.objects.filter_acl(request.user).get(pk=pk)
        return ret

    def response_add(self, request, obj, post_url_continue=None):
        ret = super().response_add(request, obj, post_url_continue)
        if '_addanother' in request.POST:
            day = request.POST['day']
            mission = request.POST['mission']
            qs = '?mission_id=%s&day=%s' % (mission, day)
            ret = HttpResponseRedirect(f'{ret.url}{qs}')
        return ret

    def response_change(self, request, obj):
        ret = super().response_change(request, obj)
        if '_addanother' in request.POST:
            day = request.POST['day']
            mission = request.POST['mission']
            qs = '?mission_id=%s&day=%s' % (mission, day)
            ret = HttpResponseRedirect(f'{ret.url}{qs}')
        return ret

    @button(
        html_attrs=NORMAL,
        visible=lambda button: button.request.GET.get('mission_id') is not None
    )
    def capture(self, request):
        changelist_fitlers = re.match(r'mission_id=(?P<mission_id>\d+)', request.GET.get('_changelist_filters'))
        mission_id = changelist_fitlers.groupdict().get('mission_id')

        expenses = Expense.objects.filter(mission_id=mission_id, image='').values_list('id', flat=True)
        if expenses:
            expenses = list(map(str, expenses))
            next, others = expenses[0], expenses[1:] if len(expenses) > 1 else []
            if others:
                request.session[EXPENSE_UPLOAD_IMAGES] = others
            url = f"{reverse('admin:missions_expense_changelist')}{next}/view_qr/"
            return HttpResponseRedirect(url)
        else:
            messages.info(request, 'There are no images left to capture')

    @button(
        html_attrs={'style': 'background-color:#0CDC6C;color:black'}
    )
    def purge_obsolete_images(self, request):
        count = 0
        storage = Expense.image.field.storage
        existing = set(Expense.objects.values_list('image', flat=True))
        offset = len(settings.MEDIA_ROOT) + 1
        for root, dirs, files in os.walk(storage.location, topdown=False):
            for name in files:
                fullname = root + '/' + name
                if fullname[offset:] not in existing:
                    os.remove(fullname)
                    count += 1
        messages.success(request, f'Cleaned {count} files')

    # FIXME: does not work ?
    @button(
        html_attrs=DANGEROUS,
        visible=lambda btn: bool(btn.original.id and btn.original.image)
    )
    def clean_image(self, request, pk):
        expense = self.model.objects.get(pk=pk)
        pathname = Path(expense.image.file.name)
        backup_path = pathname.parent.joinpath(pathname.stem + f'_{pk}{pathname.suffix}')
        shutil.copy(pathname, backup_path)
        cleaned = clean_image(expense.image.file.name)
        try:
            written = cv2.imwrite(str(pathname), cleaned)
            if written:
                url = reverse('admin:missions_expense_change', args=[pk]) + '?' + urlencode(
                    {'revert': f'{backup_path}'})
                messages.success(
                    request, mark_safe(f'New image saved. <a href="{url}">click here to revert to previous image</a>'))
            else:
                messages.warning(request, 'Could not save image')
        except Exception as e:
            messages.error(request, str(e))

    @button(
        html_attrs=DANGEROUS,
        visible=lambda btn: bool(btn.original.id)
    )
    def view_qr(self, request, pk):
        expense = self.get_object(request, pk)

        # FIXME: This cannot work as the mobile uploading the client is not authenticated so no same session!
        request.session[EXPENSE_UPLOAD_IMAGES] = []

        ref = rest_reverse('expense-upload-image', args=[pk], request=request) + f'?otp={expense.get_otp()}'

        return TemplateResponse(
            request,
            context={
                'site_header': site.site_header,
                'expense': expense,
                'ref': ref,
                'debug': True
            },
            template='admin/missions/expense/expense_qr.html')

    @button(
        html_attrs=NORMAL,
        visible=lambda btn: bool(btn.original.id)
    )
    def goto_mission(self, request, pk):
        expense = self.model.objects.get(pk=pk)
        return HttpResponseRedirect(reverse('admin:missions_mission_change', args=[expense.mission_id]))

    @button(
        html_attrs=DANGEROUS,
        visible=lambda btn: bool(btn.original.id and btn.original.image)
    )
    def rotate_left(self, request, pk):
        self._rotate_by_90(pk, request, 'left')

    @button(
        html_attrs=DANGEROUS,
        visible=lambda btn: bool(btn.original.id and btn.original.image)
    )
    def rotate_right(self, request, pk):
        self._rotate_by_90(pk, request, 'right')

    def _rotate_by_90(self, pk, request, direction: str):
        expense = self.model.objects.get(pk=pk)
        pathname = Path(expense.image.file.name)
        backup_path = pathname.parent.joinpath(pathname.stem + f'_{pk}{pathname.suffix}')
        shutil.copy(pathname, backup_path)
        try:
            turned = rotate_90(expense.image.file.name, direction)
            if turned:
                url = reverse('admin:missions_expense_change', args=[pk]) + '?' + urlencode(
                    {'revert': f'{backup_path}'})
                messages.success(
                    request,
                    mark_safe(f'Image was turned. <a href="{url}">click here to revert to previous image</a>'))
            else:
                messages.warning(request, 'Could not be turned')
        except Exception as e:
            messages.error(request, str(e))


@admin.register(Reimbursement)
class ReimbursementAdmin(ModelAdmin):
    inlines = [ExpenseInline]
