import decimal
import os
import re
import shutil
from pathlib import Path

import cv2
from admin_extra_buttons.decorators import button
from admin_extra_buttons.mixins import ExtraButtonsMixin
from adminfilters.autocomplete import AutoCompleteFilter
from adminfilters.dates import DateRangeFilter
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
from django.utils.safestring import mark_safe
from rangefilter.filters import NumericRangeFilterBuilder
from rest_framework.reverse import reverse as rest_reverse

from krm3.currencies.models import Currency
from krm3.missions.actions import create_reimbursement, get_rates
from krm3.missions.forms import ExpenseAdminForm
from krm3.core.models import Expense, Mission
from krm3.missions.session import EXPENSE_UPLOAD_IMAGES
from krm3.missions.transform import clean_image, rotate_90
from krm3.styles.buttons import DANGEROUS, NORMAL
from krm3.utils.queryset import ACLMixin


class RestrictedReimbursementMixin:
    def get_readonly_fields(self, request, obj=None):
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

    def get_queryset(self, request):
        return Expense.objects.prefetch_related('category').all()

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'currency':
            kwargs['queryset'] = Currency.objects.actives()
        return super(ExpenseInline, self).formfield_for_foreignkey(db_field, request, **kwargs)


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
        ('day', DateRangeFilter.factory(title='day YYYY-MM-DD')),
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
    actions = [get_rates, create_reimbursement]
    _resource_link = 'mission__resource'

    def lookup_allowed(self, lookup, value, request=None):
        if lookup == 'mission_id':
            return True
        return super().lookup_allowed(lookup, value, request)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('mission', 'reimbursement')

    @admin.display(description='Mission', ordering='mission')
    def mission_st(self, expense: Expense):
        txt = '%s'
        if expense.mission.status == Mission.MissionStatus.DRAFT:
            txt = '<span style="color: grey;">%s</span>'
        elif expense.mission.status == Mission.MissionStatus.CANCELLED:
            txt = '<span style="color: grey;text-decoration: line-through">%s</span>'
        return format_html(txt % expense.mission)

    @admin.display(description='Amt. currency', ordering='amount_currency')
    def colored_amount_currency(self, obj):
        if obj.payment_type.personal_expense:
            cell_html = '<span style="color: blue;">%s</span>'
        else:
            cell_html = '%s'
        # for below line, you may consider using 'format_html', instead of python's string formatting
        return format_html(cell_html % f'{obj.amount_currency} {obj.currency.iso3}')

    @admin.display(description='Amt. reimbursement', ordering='amount_reimbursement')
    def colored_amount_reimbursement(self, obj):
        if (value := obj.amount_reimbursement) and obj.amount_reimbursement < decimal.Decimal(0):
            cell_html = '<span style="color: red;">%s</span>'
            value *= decimal.Decimal(-1)
        else:
            cell_html = '%s'

        # for below line, you may consider using 'format_html', instead of python's string formatting
        return format_html(cell_html % value)

    def colored_amount_base(self, obj):
        if obj.amount_base and obj.amount_base < decimal.Decimal(0):
            cell_html = '<span style="color: red;">%s</span>'
        else:
            cell_html = '%s'
        # for below line, you may consider using 'format_html', instead of python's string formatting
        return format_html(cell_html % obj.amount_base)

    colored_amount_base.short_description = 'Amt. base'
    colored_amount_base.admin_order_field = 'amount_base'

    def link_to_reimbursement(self, obj):
        if obj.reimbursement:
            link = reverse('admin:core_reimbursement_change', args=[obj.reimbursement.id])
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

    @button(html_attrs=NORMAL, visible=lambda button: button.request.GET.get('mission_id') is not None)
    def capture(self, request):
        changelist_fitlers = re.match(r'mission_id=(?P<mission_id>\d+)', request.GET.get('_changelist_filters'))
        mission_id = changelist_fitlers.groupdict().get('mission_id')

        expenses = Expense.objects.filter(mission_id=mission_id, image='').values_list('id', flat=True)
        if expenses:
            expenses = list(map(str, expenses))
            next, others = expenses[0], expenses[1:] if len(expenses) > 1 else []
            if others:
                request.session[EXPENSE_UPLOAD_IMAGES] = others
            url = f'{reverse("admin:core_expense_changelist")}{next}/view_qr/'
            return HttpResponseRedirect(url)
        else:
            messages.info(request, 'There are no images left to capture')

    @button(html_attrs={'style': 'background-color:#0CDC6C;color:black'})
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
    @button(html_attrs=DANGEROUS, visible=lambda btn: bool(btn.original.id and btn.original.image))
    def clean_image(self, request, pk):
        expense = self.model.objects.get(pk=pk)
        pathname = Path(expense.image.file.name)
        backup_path = pathname.parent.joinpath(pathname.stem + f'_{pk}{pathname.suffix}')
        shutil.copy(pathname, backup_path)
        cleaned = clean_image(expense.image.file.name)
        try:
            written = cv2.imwrite(str(pathname), cleaned)
            if written:
                url = (
                    reverse('admin:core_expense_change', args=[pk]) + '?' + urlencode({'revert': f'{backup_path}'})
                )
                messages.success(
                    request, mark_safe(f'New image saved. <a href="{url}">click here to revert to previous image</a>')
                )
            else:
                messages.warning(request, 'Could not save image')
        except Exception as e:
            messages.error(request, str(e))

    @button(html_attrs=DANGEROUS, visible=lambda btn: bool(btn.original.id))
    def view_qr(self, request, pk):
        expense = self.get_object(request, pk)

        # FIXME: This cannot work as the mobile uploading the client is not authenticated so no same session!
        request.session[EXPENSE_UPLOAD_IMAGES] = []

        ref = (
            rest_reverse('missions:expense-upload-image', args=[pk], request=request) + f'?otp={expense.get_otp()}'
        )
        if settings.FORCE_DEBUG_SSL:
            ref = 'https' + ref[ref.index(':') :]  # force https also locally for ngrok
        return TemplateResponse(
            request,
            context={'site_header': site.site_header, 'expense': expense, 'ref': ref, 'debug': True},
            template='admin/missions/expense/expense_qr.html',
        )

    @button(html_attrs=NORMAL, visible=lambda btn: bool(btn.original.id))
    def clone(self, request, pk):
        request.session['_like'] = pk
        return HttpResponseRedirect(reverse('admin:core_expense_add'))

    @button(html_attrs=NORMAL, visible=lambda btn: bool(btn.original.id))
    def goto_mission(self, request, pk):
        expense = self.model.objects.get(pk=pk)
        return HttpResponseRedirect(reverse('admin:core_mission_change', args=[expense.mission_id]))

    @button(html_attrs=NORMAL, visible=lambda btn: bool(btn.original.id) and btn.original.reimbursement_id is not None)
    def goto_reimbursement(self, request, pk):
        expense = self.model.objects.get(pk=pk)
        return HttpResponseRedirect(reverse('admin:core_reimbursement_change', args=[expense.reimbursement_id]))

    @button(html_attrs=DANGEROUS, visible=lambda btn: bool(btn.original.id and btn.original.image))
    def rotate_left(self, request, pk):
        self._rotate_by_90(pk, request, 'left')

    @button(html_attrs=DANGEROUS, visible=lambda btn: bool(btn.original.id and btn.original.image))
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
                url = (
                    reverse('admin:core_expense_change', args=[pk]) + '?' + urlencode({'revert': f'{backup_path}'})
                )
                messages.success(
                    request, mark_safe(f'Image was turned. <a href="{url}">click here to revert to previous image</a>')
                )
            else:
                messages.warning(request, 'Could not be turned')
        except Exception as e:
            messages.error(request, str(e))
