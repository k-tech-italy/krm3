from django.template.defaultfilters import floatformat
from django.template.library import Library
from django.utils.html import format_html

register = Library()


@register.filter(is_safe=True)
def numformat(text, arg=-1):
    txt = floatformat(text, arg=arg)
    if '-' in txt:
        txt = format_html('<span style="color: red;">{}<span>', txt)
    return txt
