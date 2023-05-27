import os

import cv2
from admin_extra_buttons.decorators import button
from admin_extra_buttons.mixins import ExtraButtonsMixin
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin import ModelAdmin
from django.template.response import TemplateResponse
from mptt.admin import MPTTModelAdmin

from krm3.missions.forms import MissionAdminForm
from krm3.missions.models import Expense, ExpenseCategory, Mission, PaymentCategory, Reimbursement
from krm3.missions.transform import clean_image


@admin.register(Mission)
class MissionAdmin(ModelAdmin):
    form = MissionAdminForm


@admin.register(PaymentCategory)
class PaymentCategoryAdmin(MPTTModelAdmin):
    pass


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(MPTTModelAdmin):
    pass


@admin.register(Expense)
class ExpenseAdmin(ExtraButtonsMixin, ModelAdmin):

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
        cleaned = clean_image(expense.image.file.name)
        try:
            written = cv2.imwrite(expense.image.file.name, cleaned)
            if written:
                messages.success(request, 'New image saved')
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
