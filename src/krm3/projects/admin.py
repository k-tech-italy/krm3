from admin_extra_buttons.decorators import button
from admin_extra_buttons.mixins import ExtraButtonsMixin
from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.http import HttpResponseRedirect, HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse

from krm3.core.models import Task, Project
from krm3.projects.forms import TaskForm
from krm3.styles.buttons import NORMAL


class TaskInline(admin.TabularInline):  # noqa: D101
    model = Task
    exclude = ['color', 'on_call_price', 'overtime_price', 'travel_price']
    autocomplete_fields = ['resource']


@admin.register(Project)
class ProjectAdmin(ExtraButtonsMixin, ModelAdmin):
    search_fields = ['name']
    autocomplete_fields = ['client']
    inlines = [TaskInline]

    @button(html_attrs=NORMAL)
    def view_tasks(self, request: HttpRequest, pk: int) -> HttpResponse:
        return redirect(reverse('admin:core_task_changelist') + f'?project_id={pk}')



@admin.register(Task)
class TaskAdmin(ExtraButtonsMixin, admin.ModelAdmin):
    list_display = ('title', 'project', 'resource', 'basket_title', 'work_price')
    search_fields = ('title', 'project', 'resource', 'basket_title')
    form = TaskForm
    fieldsets = (
        (None, {
            'fields': (
                ('title', 'project', 'resource'),
                ('start_date', 'end_date'),
                ('basket_title', 'color')
            )
        }),
        ('Costs', {
            'fields': (
                ('work_price', 'overtime_price'),
                ('travel_price', 'on_call_price')
            )
        }),
    )

    @button(html_attrs=NORMAL, visible=lambda btn: bool(btn.original.id))
    def goto_project(self, request: HttpRequest, pk: int) -> HttpResponseRedirect:
        task = self.model.objects.get(pk=pk)
        return HttpResponseRedirect(reverse('admin:core_project_change', args=[task.project_id]))
