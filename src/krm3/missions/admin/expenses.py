import decimal
import os
import re
import shutil
import typing
from pathlib import Path
from typing import Any

import cv2
from admin_extra_buttons.decorators import button
from admin_extra_buttons.mixins import ExtraButtonsMixin
from adminfilters.autocomplete import AutoCompleteFilter
from adminfilters.dates import DateFilter
from adminfilters.mixin import AdminFiltersMixin
from adminfilters.num import NumberFilter
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin import ModelAdmin, site
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.http import urlencode

from rangefilter.filters import NumericRangeFilterBuilder
from rest_framework.reverse import reverse as rest_reverse

from krm3.currencies.models import Currency
from krm3.missions.actions import create_reimbursement, get_rates, reset_reimbursement
from krm3.missions.forms import ExpenseAdminForm
from krm3.core.models import Expense, Mission
from krm3.missions.session import EXPENSE_UPLOAD_IMAGES
from krm3.missions.transform import clean_image, rotate_90
from krm3.styles.buttons import DANGEROUS, NORMAL
from krm3.utils.queryset import ACLMixin

if typing.TYPE_CHECKING:
    from django.http import HttpRequest
    from django.forms import Form, Field
    from django.db.models.query import QuerySet
    from django.db.models import Field as ModelField


class RestrictedReimbursementMixin:
    def get_readonly_fields(self, request: 'HttpRequest', obj: Any = None) -> list[str]:
        ret = list(super().get_readonly_fields(request, obj))
        if not request.user.has_perm('missions.view_any_mission') and not request.user.has_perm(
            'missions.manage_any_mission'
        ):
            ret.append('reimbursement')
        return ret


class ExpenseInline(RestrictedReimbursementMixin, admin.TabularInline):  # noqa: D101
    form = ExpenseAdminForm
    model = Expense
    extra = 3
    exclude = ['amount_base', 'amount_reimbursement', 'created_ts', 'modified_ts']
    autocomplete_fields = ['mission', 'category', 'currency', 'payment_type', 'reimbursement']

    def get_queryset(self, request: 'HttpRequest') -> 'QuerySet[Expense]':
        return Expense.objects.prefetch_related('category').all()

    def formfield_for_foreignkey(self, db_field: 'ModelField', request: 'HttpRequest' = None, **kwargs) -> 'Field':
        if db_field.name == 'currency':
            kwargs['queryset'] = Currency.objects.actives()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Expense)
class ExpenseAdmin(RestrictedReimbursementMixin, ACLMixin, ExtraButtonsMixin, AdminFiltersMixin, ModelAdmin):
    readonly_fields = ['amount_base']
    form = ExpenseAdminForm
    autocomplete_fields = ['mission', 'currency', 'category', 'payment_type', 'reimbursement']
    list_display = (
        'mission_st',
        'day',
        'colored_amount_currency',
        'colored_amount_base',
        'colored_amount_reimbursement',
        'category',
        'payment_type',
        'document_type',
        'link_to_reimbursement',
        'image',
    )
    list_filter = [
        ('reimbursement', admin.EmptyFieldListFilter),
        'mission__status',
        ('mission__number', NumberFilter),
        ('mission__year', NumberFilter),
        ('amount_currency', NumericRangeFilterBuilder()),
        ('category', AutoCompleteFilter),
        ('document_type', AutoCompleteFilter),
        ('reimbursement', AutoCompleteFilter),
        ('day', DateFilter.factory(title='day YYYY-MM-DD')),
    ]
    search_fields = ['amount_currency', 'mission__number']
    fieldsets = [
        (
            None,
            {
                'fields': [
                    ('mission', 'day'),
                    ('amount_currency', 'currency'),
                    ('amount_base', 'amount_reimbursement'),
                    'detail',
                    ('category', 'payment_type', 'document_type', 'reimbursement'),
                    'image',
                ]
            },
        )
    ]
    actions = [reset_reimbursement, get_rates, create_reimbursement]
    _resource_link = 'mission__resource'

    def lookup_allowed(self, lookup: str, value: Any, request: 'HttpRequest' = None) -> bool:
        if lookup == 'mission_id':
            return True
        return super().lookup_allowed(lookup, value, request)

    def get_queryset(self, request: 'HttpRequest') -> 'QuerySet':
        return super().get_queryset(request).prefetch_related('mission', 'reimbursement')

    @admin.display(description='Mission', ordering='mission')
    def mission_st(self, expense: Expense) -> str:
        txt = '%s'
        if expense.mission.status == Mission.MissionStatus.DRAFT:
            txt = '<span style="color: grey;">%s</span>'
        elif expense.mission.status == Mission.MissionStatus.CANCELLED:
            txt = '<span style="color: grey;text-decoration: line-through">%s</span>'
        return format_html(txt % expense.mission)

    @admin.display(description='Amt. currency', ordering='amount_currency')
    def colored_amount_currency(self, obj: Expense) -> str:
        if obj.payment_type.personal_expense:
            cell_html = '<span style="color: blue;">%s</span>'
        else:
            cell_html = '%s'
        # for below line, you may consider using 'format_html', instead of python's string formatting
        return format_html(cell_html % f'{obj.amount_currency} {obj.currency.iso3}')

    @admin.display(description='Amt. reimbursement', ordering='amount_reimbursement')
    def colored_amount_reimbursement(self, obj: Expense) -> str:
        if (value := obj.amount_reimbursement) and obj.amount_reimbursement < decimal.Decimal(0):
            cell_html = '<span style="color: red;">%s</span>'
            value *= decimal.Decimal(-1)
        else:
            cell_html = '%s'

        # for below line, you may consider using 'format_html', instead of python's string formatting
        return format_html(cell_html % value)

    def colored_amount_base(self, obj: Expense) -> str:
        if obj.amount_base and obj.amount_base < decimal.Decimal(0):
            cell_html = '<span style="color: red;">%s</span>'
        else:
            cell_html = '%s'
        # for below line, you may consider using 'format_html', instead of python's string formatting
        return format_html(cell_html % obj.amount_base)

    colored_amount_base.short_description = 'Amt. base'
    colored_amount_base.admin_order_field = 'amount_base'

    def link_to_reimbursement(self, obj: Expense) -> str:
        if obj.reimbursement:
            link = reverse('admin:core_reimbursement_change', args=[obj.reimbursement.id])
            return format_html('<a href="{}">{}</a>', link, obj.reimbursement)
        return '--'

    link_to_reimbursement.short_description = 'Reimbursement'

    def formfield_for_foreignkey(self, db_field: 'ModelField', request: 'HttpRequest' = None, **kwargs) -> 'Field':
        if db_field.name == 'currency':
            kwargs['queryset'] = Currency.objects.actives()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_form(self, request: 'HttpRequest', obj: Expense = None, change: bool = False, **kwargs) -> 'Form':
        if obj and (revert := request.GET.get('revert')):
            shutil.copy(revert, obj.image.file.name)
        return super().get_form(request, obj, change, **kwargs)

    def get_changeform_initial_data(self, request: 'HttpRequest') -> dict:
        ret = super().get_changeform_initial_data(request)
        like = request.session.get('_like', None)
        if like:
            del request.session['_like']
            source = Expense.objects.get(pk=like)
            ret['mission'] = source.mission
            ret['category'] = source.category
            ret['payment_type'] = source.payment_type
            ret['document_type'] = source.document_type
            ret['day'] = source.day
            ret['currency'] = source.currency
        else:
            pk = ret.pop('mission_id', None)
            if pk:
                ret['mission'] = Mission.objects.filter_acl(request.user).get(pk=pk)
        return ret

    def response_add(self, request: 'HttpRequest', obj: Expense, post_url_continue: str = None) -> HttpResponseRedirect:
        ret = super().response_add(request, obj, post_url_continue)
        if '_addanother' in request.POST:
            day = request.POST['day']
            mission = request.POST['mission']
            qs = '?mission_id=%s&day=%s' % (mission, day)
            ret = HttpResponseRedirect(f'{ret.url}{qs}')
        return ret

    def response_change(self, request: 'HttpRequest', obj: Expense) -> HttpResponseRedirect:
        ret = super().response_change(request, obj)
        if '_addanother' in request.POST:
            day = request.POST['day']
            mission = request.POST['mission']
            qs = '?mission_id=%s&day=%s' % (mission, day)
            ret = HttpResponseRedirect(f'{ret.url}{qs}')
        return ret

    @button(html_attrs=NORMAL, visible=lambda button: button.request.GET.get('mission_id') is not None)
    def capture(self, request: 'HttpRequest') -> HttpResponseRedirect | None:
        changelist_fitlers = re.match(r'mission_id=(?P<mission_id>\d+)', request.GET.get('_changelist_filters'))
        mission_id = changelist_fitlers.groupdict().get('mission_id')

        expenses = Expense.objects.filter(mission_id=mission_id, image='').values_list('id', flat=True)
        if expenses:
            expenses = list(map(str, expenses))
            next_, others = expenses[0], expenses[1:] if len(expenses) > 1 else []
            if others:
                request.session[EXPENSE_UPLOAD_IMAGES] = others
            url = f'{reverse("admin:core_expense_changelist")}{next_}/view_qr/'
            return HttpResponseRedirect(url)
        messages.info(request, 'There are no images left to capture')
        return None

    @button(html_attrs={'style': 'background-color:#0CDC6C;color:black'})
    def purge_obsolete_images(self, request: 'HttpRequest') -> None:
        count = 0
        storage = Expense.image.field.storage
        existing = set(Expense.objects.values_list('image', flat=True))
        offset = len(settings.MEDIA_ROOT) + 1
        for root, _, files in os.walk(storage.location, topdown=False):
            for name in files:
                fullname = root + '/' + name
                if fullname[offset:] not in existing:
                    os.remove(fullname)
                    count += 1
        messages.success(request, f'Cleaned {count} files')

    # FIXME: does not work ?
    @button(html_attrs=DANGEROUS, visible=lambda btn: bool(btn.original.id and btn.original.image))
    def clean_image(self, request: 'HttpRequest', pk: int) -> None:
        expense = self.model.objects.get(pk=pk)
        pathname = Path(expense.image.file.name)
        backup_path = pathname.parent.joinpath(pathname.stem + f'_{pk}{pathname.suffix}')
        shutil.copy(pathname, backup_path)
        cleaned = clean_image(expense.image.file.name)
        try:
            written = cv2.imwrite(str(pathname), cleaned)
            if written:
                url = reverse('admin:core_expense_change', args=[pk]) + '?' + urlencode({'revert': f'{backup_path}'})
                messages.success(
                    request,
                    format_html('New image saved. <a href="{}">click here to revert to previous image</a>', url),
                )
            else:
                messages.warning(request, 'Could not save image')
        except Exception as e:  # noqa: BLE001
            messages.error(request, str(e))

    @button(html_attrs=DANGEROUS, visible=lambda btn: bool(btn.original.id))
    def view_qr(self, request: 'HttpRequest', pk: int) -> TemplateResponse:
        expense = self.get_object(request, pk)

        # FIXME: This cannot work as the mobile uploading the client is not authenticated so no same session!
        request.session[EXPENSE_UPLOAD_IMAGES] = []

        ref = rest_reverse('missions:expense-upload-image', args=[pk], request=request) + f'?otp={expense.get_otp()}'
        if settings.FORCE_DEBUG_SSL:
            ref = 'https' + ref[ref.index(':') :]  # force https also locally for ngrok
        return TemplateResponse(
            request,
            context={'site_header': site.site_header, 'expense': expense, 'ref': ref, 'debug': True},
            template='admin/missions/expense/expense_qr.html',
        )

    @button(html_attrs=NORMAL, visible=lambda btn: bool(btn.original.id))
    def clone(self, request: 'HttpRequest', pk: int) -> HttpResponseRedirect:
        request.session['_like'] = pk
        return HttpResponseRedirect(reverse('admin:core_expense_add'))

    @button(html_attrs=NORMAL, visible=lambda btn: bool(btn.original.id))
    def goto_mission(self, request: 'HttpRequest', pk: int) -> HttpResponseRedirect:
        expense = self.model.objects.get(pk=pk)
        return HttpResponseRedirect(reverse('admin:core_mission_change', args=[expense.mission_id]))

    @button(html_attrs=NORMAL, visible=lambda btn: bool(btn.original.id) and btn.original.reimbursement_id is not None)
    def goto_reimbursement(self, request: 'HttpRequest', pk: int) -> HttpResponseRedirect:
        expense = self.model.objects.get(pk=pk)
        return HttpResponseRedirect(reverse('admin:core_reimbursement_change', args=[expense.reimbursement_id]))

    @button(html_attrs=DANGEROUS, visible=lambda btn: bool(btn.original.id and btn.original.image))
    def rotate_left(self, request: 'HttpRequest', pk: int) -> None:
        self._rotate_by_90(pk, request, 'left')

    @button(html_attrs=DANGEROUS, visible=lambda btn: bool(btn.original.id and btn.original.image))
    def rotate_right(self, request: 'HttpRequest', pk: int) -> None:
        self._rotate_by_90(pk, request, 'right')

    def _rotate_by_90(self, pk: int, request: 'HttpRequest', direction: str) -> None:
        expense = self.model.objects.get(pk=pk)
        pathname = Path(expense.image.file.name)
        backup_path = pathname.parent.joinpath(pathname.stem + f'_{pk}{pathname.suffix}')
        shutil.copy(pathname, backup_path)
        try:
            turned = rotate_90(expense.image.file.name, direction)
            if turned:
                url = reverse('admin:core_expense_change', args=[pk]) + '?' + urlencode({'revert': f'{backup_path}'})
                messages.success(
                    request,
                    format_html('Image was turned. <a href="{}">click here to revert to previous image</a>', url),
                )
            else:
                messages.warning(request, 'Could not be turned')
        except Exception as e:  # noqa: BLE001
            messages.error(request, str(e))
