"""SQL admin panel module."""

import base64
import urllib.parse

import sqlparse
from django import forms
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import DEFAULT_DB_ALIAS, connections
from django.http import JsonResponse
from django.shortcuts import render

QUICK_SQL = {
    'Show Tables': 'SELECT * FROM information_schema.tables;',
    'Show Indexes': 'SELECT tablename, indexname, indexdef FROM pg_indexes '
    "WHERE schemaname='public' ORDER BY tablename, indexname;",
    'Describe Table': 'SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME=[table_name];',
    'Show Contraints': """SELECT con.*
       FROM pg_catalog.pg_constraint con
            INNER JOIN pg_catalog.pg_class rel
                       ON rel.oid = con.conrelid
            INNER JOIN pg_catalog.pg_namespace nsp
                       ON nsp.oid = connamespace;""",
}


class SQLForm(forms.Form):  # noqa: D101
    command = forms.CharField(widget=forms.Textarea(attrs={'style': 'width:100%;height:40px'}))

    def clean_command(self):  # noqa: D102
        value = self.cleaned_data.pop('command')
        value = urllib.parse.unquote(base64.b64decode(value).decode())

        try:
            statements = sqlparse.split(value)
            if len(statements) > 1:
                raise ValidationError('Only one statement is allowed')
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(e)
        return value


def save_expression(request):  # noqa: D103
    form = SQLForm(request.POST)
    if form.is_valid():
        name = request.POST['name']
        user = request.user
        sql_stms = user.system_options.get('sql_stm', {})
        if len(sql_stms) < 5:
            sql_stms[name] = form.cleaned_data['command']
            user.system_options['sql_stm'] = sql_stms
            user.save()

        response = {'message': 'Saved'}
    else:
        response = {'error': form.errors}
    return JsonResponse(response)


def panel_sql(self, request, extra_context=None):  # noqa: D103
    if not request.user.is_superuser:
        raise PermissionDenied
    context = self.each_context(request)
    context['buttons'] = QUICK_SQL
    if request.method == 'POST':
        if request.GET.get('op', '') == 'save':
            return save_expression(request)

        form = SQLForm(request.POST)
        response = {'result': [], 'error': None, 'stm': ''}
        if form.is_valid():
            try:
                cmd = form.cleaned_data['command']
                # stm = urllib.parse.unquote(base64.b64decode(cmd).decode())
                response['stm'] = sqlparse.format(cmd)
                if request.user.is_superuser:
                    conn = connections[DEFAULT_DB_ALIAS]
                else:
                    conn = connections['read_only']
                cursor = conn.cursor()
                cursor.execute(cmd)
                if cursor.pgresult_ptr is not None:
                    response['result'] = cursor.fetchall()
                else:
                    response['result'] = ['Success']
            except Exception as e:
                response['error'] = str(e)
        else:
            response['error'] = str(form.errors)
        return JsonResponse(response)
    form = SQLForm()
    context['form'] = form
    return render(request, 'admin/console/sql.html', context)


panel_sql.verbose_name = 'SQL'
