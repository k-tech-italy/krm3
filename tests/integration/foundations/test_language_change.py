import time

import pytest
from django.shortcuts import reverse
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC


@pytest.mark.xfail(reason="This will fail until the frontend counterpart of this feature is merged.")
@pytest.mark.selenium
def test_user_selects_preferred_language(browser, resource):
    browser.driver.delete_all_cookies()
    browser.login_as_user(resource.user)

    # Wait for login to complete by checking for the session cookie
    WebDriverWait(browser, 2).until(
        lambda driver: any(cookie['name'] == 'sessionid' for cookie in driver.get_cookies())
    )
    browser.driver.get(str(browser.live_server_url) + reverse('user_resource', args=[resource.user.id]))

    # Wait for the language dropdown to be present and interactable
    language_dropdown = WebDriverWait(browser, 10).until(
        EC.element_to_be_clickable(('id', 'id_preferred_language'))
    )

    select = Select(language_dropdown)
    select.select_by_value('it')
    submit_button = browser.find_element('css selector', 'button[type="submit"]')
    submit_button.click()

    browser.driver.get(str(browser.live_server_url) + '/')

    # Wait for the NEW page to fully load
    WebDriverWait(browser, 5).until(
        lambda driver: 'user_resource' not in browser.live_server_url
    )
    # FIXME: find a way to remove the sleep without breaking the test in headless mode
    time.sleep(0.1)
    browser.assert_element_present('//h1[text()="Benvenuta!"]')
    cookies = browser.get_cookies()
    django_language_cookie = next(
        (cookie for cookie in cookies if cookie['name'] == 'django_language'),
        None
    )
    assert django_language_cookie['value'] == 'it'
