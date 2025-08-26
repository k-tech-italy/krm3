from datetime import datetime
from typing import Any

from django import template

register = template.Library()
@register.filter
def weekday_short_it(date: datetime.date) -> str:
    italian_weekdays_short = [
        "Lun",
        "Mar",
        "Mer",
        "Gio",
        "Ven",
        "Sab",
        "Dom"
    ]
    return italian_weekdays_short[date.weekday()]

@register.filter
def get(dict_obj: Any, key: Any) -> Any:
    return dict_obj.get(key, '')

@register.filter
def is_list(obj: Any) -> bool:
    return isinstance(obj, list)
