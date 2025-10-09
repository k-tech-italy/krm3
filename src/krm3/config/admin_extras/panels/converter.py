"""Converter admin panel module."""

from dateutil.parser import parse
from django import forms
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import JsonResponse
from django.shortcuts import render
from tabulate import tabulate

from krm3.currencies.models import Rate


def _parse_entries(value):
    results = []
    lines: list[str] = value.splitlines()

    for line in lines:
        dt, amt, currency = [x.strip() for x in line.split(',') if line.count(',') == 2]
        dt = parse(dt, dayfirst=True)
        currency = currency.upper()
        results.append({'dt': dt, 'amt': float(amt), 'currency': currency})
    return results


class ConverterForm(forms.Form):  # noqa: D101
    CURRENCY_CHOICES = (
        ('EUR', 'EUR'),
        ('USD', 'USD'),
        ('GBP', 'GBP'),
        ('XOF', 'XOF'),
    )
    entries = forms.CharField(widget=forms.Textarea())
    to_currency = forms.ChoiceField(choices=CURRENCY_CHOICES)

    def clean_entries(self):  # noqa: D102
        value: str = self.cleaned_data.pop('entries')
        try:
            results = _parse_entries(value)
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(e)
        return results


def save_expression(request):  # noqa: D103
    form = ConverterForm(request.POST)
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


def panel_converter(self, request, extra_context=None):  # noqa: D103
    if not request.user.is_superuser:
        raise PermissionDenied
    context = self.each_context(request)
    if request.method == 'POST':
        form = ConverterForm(request.POST)
        if form.is_valid():
            to_currency = form.cleaned_data['to_currency']
            table = []
            for e in form.cleaned_data['entries']:
                rate = Rate.for_date(e['dt'])
                table.append(
                    [
                        e['dt'].strftime('%Y-%M-%D'),
                        e['amt'],
                        curr := e['currency'],
                        rate.convert(e['amt'], from_currency=curr, to_currency=to_currency),
                    ]
                )
            headers = ['date', 'amount', 'currency', to_currency]
            context['results'] = tabulate(table, headers, tablefmt='html')
            # try:
            #     cmd = form.cleaned_data['command']
            #     # stm = urllib.parse.unquote(base64.b64decode(cmd).decode())
            #     response['stm'] = sqlparse.format(cmd)
            #     if request.user.is_superuser:
            #         conn = connections[DEFAULT_DB_ALIAS]
            #     else:
            #         conn = connections['read_only']
            #     cursor = conn.cursor()
            #     cursor.execute(cmd)
            #     if cursor.pgresult_ptr is not None:
            #         response['result'] = cursor.fetchall()
            #     else:
            #         response['result'] = ['Success']
            # except Exception as e:
            #     response['error'] = str(e)
        else:
            context['errors'] = str(form.errors)
    else:
        form = ConverterForm()
    context['form'] = form
    return render(request, 'admin/console/converter.html', context)


panel_converter.verbose_name = 'Converter utility'
