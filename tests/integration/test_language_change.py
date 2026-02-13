import pytest
from django.shortcuts import reverse
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC


@pytest.mark.selenium
def test_user_selects_preferred_language(browser, resource):
    browser.login_as_user(resource.user)

    # Wait for login to complete by checking for the session cookie
    WebDriverWait(browser, 10).until(
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

    WebDriverWait(browser, 10).until(
        EC.presence_of_element_located(('id', 'id_preferred_language'))
    )

    language_dropdown = browser.find_element('id', 'id_preferred_language')
    select = Select(language_dropdown)
    assert select.first_selected_option.get_attribute('value') == 'it'

    cookies = browser.get_cookies()
    django_language_cookie = next(
        (cookie for cookie in cookies if cookie['name'] == 'django_language'),
        None
    )
    assert django_language_cookie is not None
    assert django_language_cookie['value'] == 'it'

    browser.driver.get(str(browser.live_server_url) + '/')
    assert "Benvenuta" in browser.get_page_source()