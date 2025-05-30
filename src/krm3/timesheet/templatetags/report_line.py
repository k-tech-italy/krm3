from django import template
from django.utils.safestring import mark_safe, SafeString

register = template.Library()


@register.simple_tag
def report_line(key: str, label:str, data: dict) -> SafeString:
    cells = '\n'.join([f'<td class="p-1">{c if c else ""}</td>' for c in data[key]])
    result = f"""
        <tr>
            <td class="text-left p-1">{label}</td>
            {cells}
        </tr>
    """
    return mark_safe(result)  # noqa: S308
