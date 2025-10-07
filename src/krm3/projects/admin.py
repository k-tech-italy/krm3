import typing
from typing import cast

from admin_extra_buttons.decorators import button
from admin_extra_buttons.mixins import ExtraButtonsMixin
from adminfilters.autocomplete import AutoCompleteFilter
from adminfilters.dates import DateRangeFilter
from adminfilters.mixin import AdminFiltersMixin
from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse

from krm3.core.models import Project, Task
from krm3.projects.forms import TaskForm
from krm3.styles.buttons import NORMAL

if typing.TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse

    from krm3.core.models.auth import User


class TaskInline(admin.TabularInline):  # noqa: D101
    model = Task
    exclude = ['color', 'on_call_price', 'overtime_price', 'travel_price']
    autocomplete_fields = ['resource']


@admin.register(Project)
class ProjectAdmin(ExtraButtonsMixin, AdminFiltersMixin, ModelAdmin):
    search_fields = ('name',)
    list_display = ('client', 'name', 'start_date', 'end_date')
    list_filter = (
        ('client', AutoCompleteFilter),
        ('start_date', DateRangeFilter.factory(title='from YYYY-MM-DD')),
        ('end_date', DateRangeFilter.factory(title='to YYYY-MM-DD')),
    )
    autocomplete_fields = ['client']
    inlines = [TaskInline]

    @button(html_attrs=NORMAL)
    def view_tasks(self, request: "HttpRequest", pk: int) -> "HttpResponse":
        return redirect(reverse('admin:core_task_changelist') + f'?project_id={pk}')


@admin.register(Task)
class TaskAdmin(ExtraButtonsMixin, AdminFiltersMixin, admin.ModelAdmin):
    form = TaskForm
    list_display = ('project', 'title', 'resource', 'basket_title', 'start_date', 'end_date')
    search_fields = ('title', 'project__name', 'resource__first_name', 'resource__last_name', 'basket_title')
    list_filter = [
        ('project', AutoCompleteFilter),
        ('resource', AutoCompleteFilter),
        ('basket_title', AutoCompleteFilter),
    ]
    autocomplete_fields = ['project', 'resource']

    def get_fieldsets(self, request: 'HttpRequest', obj: Task = ...) -> typing.Iterable:
        fieldsets = [
            (
                None,
                {'fields': (('title', 'project', 'resource'), ('start_date', 'end_date'), ('basket_title', 'color'))},
            ),
        ]
        user = cast('User', request.user)
        if obj is None or user.has_any_perm('view_any_task_costs', 'manage_any_task_costs'):
            fieldsets.append(
                ('Costs', {'fields': (('work_price', 'overtime_price'), ('travel_price', 'on_call_price'))})
            )

        return fieldsets

    def get_changeform_initial_data(self, request: "HttpRequest") -> dict:
        ret = super().get_changeform_initial_data(request)
        like = request.session.get('_like', None)
        if like:
            del request.session['_like']
            source = Task.objects.get(pk=like)
            ret['title'] = source.title
            ret['project'] = source.project
            ret['basket_title'] = source.basket_title
            ret['start_date'] = source.start_date
            ret['work_price'] = source.work_price
        else:
            pk = ret.pop('project_id', None)
            if pk:
                ret['project'] = Project.objects.get(pk=pk)
        return ret

    @button(html_attrs=NORMAL, visible=lambda btn: bool(btn.original.id))
    def clone(self, request: "HttpRequest", pk: int) -> HttpResponseRedirect:
        request.session['_like'] = pk
        return HttpResponseRedirect(reverse('admin:core_task_add'))

    @button(html_attrs=NORMAL, visible=lambda btn: bool(btn.original.id))
    def goto_project(self, request: "HttpRequest", pk: int) -> HttpResponseRedirect:
        task = self.model.objects.get(pk=pk)
        return HttpResponseRedirect(reverse('admin:core_project_change', args=[task.project_id]))

    @button(html_attrs=NORMAL, visible=lambda btn: bool(btn.original.id))
    def view_entries(self, request: 'HttpRequest', pk: int) -> HttpResponseRedirect:
        url = reverse('admin:core_timeentry_changelist') + f'?task_id={pk}'
        return HttpResponseRedirect(url)
