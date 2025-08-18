from django import template
from django.utils.safestring import mark_safe, SafeString

register = template.Library()

@register.simple_tag
def nav_bar(elements: dict[str, str]) -> SafeString | str:
    """
    Generate navigation bar HTML code.

        Each item in the `elements` dictionary represents a navigation link:
        - key (str): the visible text of the link,
        - value (str): the URL the link points to.
    """

    def nav_item_html(element: str) -> str:
        return f"""
            <li>
                <a href="{elements[element]}" class="block py-2 px-3 text-gray-900 rounded-sm hover:bg-gray-100
                    md:hover:bg-transparent md:hover:text-blue-700 md:p-0 md:dark:hover:text-blue-500
                    dark:text-white dark:hover:bg-gray-700 dark:hover:text-white md:dark:hover:bg-transparent
                    dark:border-gray-700">
                    {element}
                </a>
            </li>
        """

    nav_items = "\n".join(map(nav_item_html, elements.keys()))

    result = f"""
        <nav class="bg-white dark:bg-gray-900 fixed w-full z-20 top-0 start-0 border-b
                border-gray-200 dark:border-gray-600 mb-20">
            <div class="max-w-screen-xl flex flex-wrap items-center justify-between mx-auto p-4">
                <a href="/" class="flex items-center space-x-3 rtl:space-x-reverse">
                    <span class="text-xl font-bold text-gray-900">KRM³</span>
                </a>
                <div class="flex md:order-2 space-x-3 md:space-x-0 rtl:space-x-reverse">
                    <button data-collapse-toggle="navbar-sticky" type="button"
                        class="inline-flex items-center p-2 w-10 h-10 justify-center text-sm text-gray-500 rounded-lg
                            md:hidden hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-200
                            dark:text-gray-400 dark:hover:bg-gray-700 dark:focus:ring-gray-600"
                        aria-controls="navbar-sticky" aria-expanded="false">
                        <span class="sr-only">Open main menu</span>
                        <svg class="w-5 h-5" aria-hidden="true" xmlns="http://www.w3.org/2000/svg"
                            fill="none" viewBox="0 0 17 14">
                            <path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"
                                stroke-width="2" d="M1 1h15M1 7h15M1 13h15"/>
                        </svg>
                    </button>
                </div>
                <div class="items-center justify-between hidden w-full md:flex md:w-auto md:order-1" id="navbar-sticky">
                    <ul class="flex flex-col p-4 md:p-0 mt-4 font-medium border border-gray-100 rounded-lg bg-gray-50
                        md:space-x-8 rtl:space-x-reverse md:flex-row md:mt-0 md:border-0 md:bg-white
                        dark:bg-gray-800 md:dark:bg-gray-900 dark:border-gray-700">
                        {nav_items}
                    </ul>
                </div>
            </div>
        </nav>
    """
    return mark_safe(result)
