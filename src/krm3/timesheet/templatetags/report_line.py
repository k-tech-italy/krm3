from django import template
from django.utils.safestring import mark_safe, SafeString

register = template.Library()


@register.simple_tag
def report_line(key: str, label:str, data: dict, is_alt:bool = False) -> SafeString | str:
    if key not in data:
        return ""
    cells = '\n'.join([f'<td class="p-1 border border-1 text-center">{c if c else ""}</td>' for c in data[key]])
    row_color = "bg-neutral-300" if is_alt else "bg-neutral-200"
    result = f"""
        <tr class="{row_color} dark:bg-neutral-600!">
            <td class="border border-1 text-left p-1 ">{label}</td>
            {cells}
        </tr>
    """
    return mark_safe(result)  # noqa: S308
