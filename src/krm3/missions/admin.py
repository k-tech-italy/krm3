import os
import shutil
from pathlib import Path

import cv2
from admin_extra_buttons.decorators import button
from admin_extra_buttons.mixins import ExtraButtonsMixin
from adminfilters.autocomplete import AutoCompleteFilter
from adminfilters.dates import DateRangeFilter
from adminfilters.mixin import AdminFiltersMixin
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin import ModelAdmin
from django.http.response import HttpResponseRedirect
from django.shortcuts import redirect, reverse
from django.template.response import TemplateResponse
from django.utils.http import urlencode
from django.utils.safestring import mark_safe
from mptt.admin import MPTTModelAdmin

from krm3.missions.forms import MissionAdminForm
from krm3.missions.models import Expense, ExpenseCategory, Mission, PaymentCategory, Reimbursement
from krm3.missions.transform import clean_image


@admin.register(Mission)
class MissionAdmin(ExtraButtonsMixin, AdminFiltersMixin, ModelAdmin):
    form = MissionAdminForm
    autocomplete_fields = ['project']
    search_fields = ['resource__first_name', 'resource__last_name', 'title', 'city', 'number']

    list_display = ('number', 'resource', 'project', 'title', 'from_date', 'to_date', 'city')
    list_filter = (
        'resource',
        ('project', AutoCompleteFilter),
        ('city', AutoCompleteFilter),
        ('from_date', DateRangeFilter),
        ('to_date', DateRangeFilter),
    )

    @button()
    def add_expense(self, request, pk):
        mission = Mission.objects.get(pk=pk)
        from_date = mission.from_date.strftime('%Y-%m-%d')
        return redirect(reverse('admin:missions_expense_add') + f'?mission_id={pk}&day={from_date}')


@admin.register(PaymentCategory)
class PaymentCategoryAdmin(MPTTModelAdmin):
    pass


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(MPTTModelAdmin):
    pass


@admin.register(Expense)
class ExpenseAdmin(ExtraButtonsMixin, AdminFiltersMixin, ModelAdmin):
    list_display = ('mission', 'day', 'amount_currency', 'category')
    list_filter = (
        ('mission__resource', AutoCompleteFilter),
        'mission__title',
    )
    fieldsets = [
        (
            None,
            {
                'fields': [
                    ('mission', 'day'),
                    ('amount_currency', 'amount_base', 'amount_reimbursement'),
                    'detail',
                    ('category', 'payment_type', 'reimbursement'),
                    'image']
            }
        )
    ]

    autocomplete_fields = ['mission']

    def get_form(self, request, obj=None, change=False, **kwargs):
        if obj and (revert := request.GET.get('revert')):
            shutil.copy(revert, obj.image.file.name)
        return super().get_form(request, obj, change, **kwargs)

    def get_changeform_initial_data(self, request):
        ret = super().get_changeform_initial_data(request)
        pk = ret.pop('mission_id', None)
        if pk:
            ret['mission'] = Mission.objects.get(pk=pk)
        return ret

    def response_add(self, request, obj, post_url_continue=None):
        ret = super().response_add(request, obj, post_url_continue)
        if "_addanother" in request.POST:
            day = request.POST['day']
            mission = request.POST['mission']
            qs = '?mission_id=%s&day=%s' % (mission, day)
            ret = HttpResponseRedirect(f'{ret.url}{qs}')
        return ret

    def response_change(self, request, obj):
        ret = super().response_change(request, obj)
        if "_addanother" in request.POST:
            day = request.POST['day']
            mission = request.POST['mission']
            qs = '?mission_id=%s&day=%s' % (mission, day)
            ret = HttpResponseRedirect(f'{ret.url}{qs}')
        return ret

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

    # FIXME: does not work
    @button(
        html_attrs={'style': 'background-color:#DC6C6C;color:black'},
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
        html_attrs={'style': 'background-color:#DC6C6C;color:black'},
        visible=lambda btn: bool(btn.original.id)
    )
    def view_qr(self, request, pk):
        expense = self.model.objects.get(pk=pk)
        return TemplateResponse(
            request,
            context={'pk': pk, 'ref': f'{pk}-{expense.get_otp()}'},
            template='admin/missions/expense/expense_qr.html')


@admin.register(Reimbursement)
class ReimbursementAdmin(ModelAdmin):
    pass
