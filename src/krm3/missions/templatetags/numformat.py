from django.template.defaultfilters import floatformat
from django.template.library import Library
from django.utils.safestring import mark_safe

register = Library()


@register.filter(is_safe=True)
def numformat(text, arg=-1):
    txt = floatformat(text, arg=arg)
    if '-' in txt:
        txt = mark_safe(f'<span style="color: red;">{txt}<span>')
    return txt
