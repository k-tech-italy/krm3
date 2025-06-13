from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from seleniumbase import BaseCase


class MaxParentsReached(NoSuchElementException):
    pass


def find_relative(obj, selector_type, path, max_parents=3):
    """Tries to find a SINGLE element with a common ancestor"""
    for c in range(max_parents, 0, -1):
        try:
            elems = obj.find_elements(selector_type, f"./{'../' * c}/{path}")
            if len(elems) == 1:
                return elems[0]
        except Exception:  # noqa: BLE001
            if max_parents == c:
                raise MaxParentsReached() from None
    raise NoSuchElementException()


def parent_element(obj, up=1):
    return obj.find_elements(By.XPATH, f".{'/..' * up}")


class AppSeleniumTC(BaseCase):
    live_server_url: str = ''

    def setUp(self, masterqa_mode=False):
        super().setUp()
        super().setUpClass()

    def tearDown(self):
        self.save_teardown_screenshot()
        super().tearDown()

    def base_method(self):
        pass

    def open(self, url: str):
        self.maximize_window()
        return super().open(f'{self.live_server_url}{url}')

    def select2_select(self, element_id: str, value: str):
        self.slow_click(f'span[aria-labelledby=select2-{element_id}-container]')
        self.wait_for_element_visible('input.select2-search__field')
        self.click(f"li.select2-results__option:contains('{value}')")
        self.wait_for_element_absent('input.select2-search__field')

    def login_as_user(self, user=None):
        if user is not None:
            self.admin_user = user
        self.open('/login')
        self.type('input[name=username]', f'{self.admin_user.username}')
        self.type('input[name=password]', f'{self.admin_user._password}')
        self.click('button[type="submit"]')
        self.wait_for_ready_state_complete()

    def login(self):
        self.open('/admin')
        if self.get_current_url() == f'{self.live_server_url}/admin/login/?next=/admin/':
            self.type('input[name=username]', f'{self.admin_user.username}')
            self.type('input[name=password]', f'{self.admin_user._password}')
            self.submit('input[value="Log in"]')
            self.wait_for_ready_state_complete()

    def is_required(self, element: str) -> bool:
        el = self.wait_for_element_visible(element)
        return el.parent.find_element('label>span').text == '(required)'

    def get_field_error(self, element: str) -> bool:
        return self.wait_for_element_visible(f'fieldset.{element} ul.errorlist').text


AppTestBrowser = AppSeleniumTC
