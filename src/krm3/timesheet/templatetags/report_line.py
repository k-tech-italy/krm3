from django import template
from django.utils.safestring import SafeString
from django.utils.html import format_html, format_html_join

register = template.Library()


@register.simple_tag
def report_line(key: str, label:str, data: dict, is_alt:bool = False) -> SafeString | str:
    if key not in data:
        return ""
    cells = format_html_join(
        '\n',
        '<td class="p-1 border border-1 text-center">{}</td>',
        ((c if c else "",) for c in data[key])
    )
    row_color = "bg-neutral-300" if is_alt else "bg-neutral-200"

    return format_html("""
        <tr class="{} dark:bg-neutral-600!">
            <td class="border border-1 text-left p-1 ">{}</td>
            {}
        </tr>
    """, row_color, label, cells)
