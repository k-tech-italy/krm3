from django import template
from django.utils.safestring import SafeString
from django.utils.html import format_html, format_html_join

register = template.Library()

@register.simple_tag(takes_context=True)
def nav_bar(context, elements: dict[str, str], logout_url: str = None) -> SafeString | str:
    """
    Generate navigation bar HTML code.

        Each item in the `elements` dictionary represents a navigation link:
        - key (str): the visible text of the link,
        - value (str): the URL the link points to.
    """

    def nav_item_html(element: str) -> SafeString:
        return format_html("""
            <li>
                <a href="{}" class="block py-2 px-3 text-gray-900 rounded-sm hover:bg-gray-100
                    md:hover:bg-transparent md:hover:text-blue-700 md:p-0 md:dark:hover:text-blue-500
                    dark:text-white dark:hover:bg-gray-700 dark:hover:text-white md:dark:hover:bg-transparent
                    dark:border-gray-700">
                    {}
                </a>
            </li>
        """, elements[element], element)

    nav_items = "\n".join(map(nav_item_html, elements.keys()))

    nav_items = format_html_join(
        "\n",
    """
        <li><a href="{}" class="block py-2 px-3 text-gray-900 rounded-sm hover:bg-gray-100
                    md:hover:bg-transparent md:hover:text-blue-700 md:p-0 md:dark:hover:text-blue-500
                    dark:text-white dark:hover:bg-gray-700 dark:hover:text-white md:dark:hover:bg-transparent
                    dark:border-gray-700">{}</a></li>
        """,
        ((url, name) for name, url in elements.items())
    )

    logout_button=""
    if logout_url:
        csrf_token = context.get('csrf_token', '')
        logout_button = format_html("""
            <form method="post" action="{}" class="inline">
                <input type="hidden" name="csrfmiddlewaretoken" value="{}">
                <button type="submit" class="block py-2 px-3 text-red-600 rounded-sm hover:bg-red-50
                    md:hover:bg-transparent md:hover:text-red-700 md:p-0 md:dark:hover:text-red-400
                    dark:text-red-400 dark:hover:bg-red-900 dark:hover:text-red-300 md:dark:hover:bg-transparent
                    dark:border-gray-700 border-0 bg-transparent cursor-pointer font-medium">
                    Logout
                </button>
            </form>
        """, logout_url, csrf_token)

    return format_html("""
            <nav class="bg-white dark:bg-gray-900 fixed w-full z-20 top-0 start-0 border-b
                    border-gray-200 dark:border-gray-600 mb-20">
                <div class="max-w-screen-xl flex flex-wrap items-center justify-between mx-auto p-4">
                    <a href="/" class="flex items-center space-x-3 rtl:space-x-reverse">
                        <span class="text-xl font-bold text-gray-900 dark:text-white">KRM³</span>
                    </a>
                    <div class="items-center justify-between w-full md:flex md:w-auto" id="navbar-sticky">
                        <ul class="flex flex-col p-4 mt-4 font-medium border border-gray-100 rounded-lg bg-gray-50
                            md:space-x-8 rtl:space-x-reverse md:flex-row md:mt-0 md:border-0 md:bg-white
                            dark:bg-gray-800 md:dark:bg-gray-900 dark:border-gray-700">
                            {}
                        </ul>
                    </div>
                    {}
                </div>
            </nav>
        """, nav_items, logout_button)
