import decimal
import json
import os
import re
import shutil
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
from django.utils.http import urlencode
from django.utils.safestring import mark_safe
from mptt.admin import MPTTModelAdmin
from rest_framework.reverse import reverse as rest_reverse

from krm3.currencies.models import Currency
from krm3.missions.forms import ExpenseAdminForm, MissionAdminForm, MissionsImportForm
from krm3.missions.impexp.export import MissionExporter
from krm3.missions.impexp.imp import MissionImporter
from krm3.missions.models import Expense, ExpenseCategory, Mission, PaymentCategory, Reimbursement
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

    class Meta:
        model = Expense
        exclude = ('mission', 'created_ts', 'modified_ts', 'image')


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

        qs = mission.expense_set.all()
        update_rates(qs)

        expenses = ExpenseTable(qs)

        summary = {'Spese risorsa': decimal.Decimal(0.0), 'Rimborsate': decimal.Decimal(0.0)}
        for expense in qs:
            summary['Spese risorsa'] += expense.amount_base or decimal.Decimal(0.0)
            summary['Rimborsate'] += expense.amount_reimbursement or decimal.Decimal(0.0)
        summary['Da rimborsare'] = summary['Spese risorsa'] - summary['Rimborsate']

        return TemplateResponse(
            request,
            context={
                'site_header': site.site_header,
                'mission': mission,
                'expenses': expenses,
                'summary': summary,
                'base': settings.CURRENCY_BASE
            },
            template='admin/missions/mission/summary.html')

    @button(
        html_attrs=NORMAL,
        visible=lambda btn: bool(btn.original.id)
    )
    def view_expenses(self, request, pk):
        url = reverse('admin:missions_expense_changelist') + f'?mission_id={pk}'
        return HttpResponseRedirect(url)


@admin.register(PaymentCategory)
class PaymentCategoryAdmin(MPTTModelAdmin):
    search_fields = ['title']
    autocomplete_fields = ['parent']


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(MPTTModelAdmin):
    search_fields = ['title']
    autocomplete_fields = ['parent']


@admin.action(description='Get the rates for the dates')
def get_rates(modeladmin, request, queryset):
    expenses = queryset.filter(amount_base__isnull=True)
    ret = expenses.count()
    qs = expenses.all()
    update_rates(qs)
    messages.success(request, f'Converted {ret} amounts')


@admin.register(Expense)
class ExpenseAdmin(ACLMixin, ExtraButtonsMixin, AdminFiltersMixin, ModelAdmin):
    readonly_fields = ['amount_base']
    form = ExpenseAdminForm
    autocomplete_fields = ['mission', 'missions__title', 'currency', 'category', 'payment_type']
    list_display = ('mission', 'day', 'amount_currency', 'currency', 'amount_base', 'category', 'payment_type', 'image')
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
    actions = [get_rates]

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
    pass
