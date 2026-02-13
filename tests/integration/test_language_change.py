import pytest
from django.shortcuts import reverse


@pytest.mark.selenium
def test_user_selects_preferred_language(browser, resource):
    browser.login_as_user(resource.user)

    # Navigate to the page
    browser.get(reverse('user_resource', args=[resource.user.id]))

    # Find the language dropdown by its ID
    language_dropdown = browser.find_element('id', 'id_preferred_language')

    # Change language to 'fr' via the dropdown
    from selenium.webdriver.support.ui import Select
    select = Select(language_dropdown)
    select.select_by_value('fr')

    # Submit the form
    submit_button = browser.find_element('css selector', 'button[type="submit"]')
    submit_button.click()

    # Wait for the page to reload/update
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    WebDriverWait(browser, 10).until(
        EC.presence_of_element_located(('id', 'id_preferred_language'))
    )

    # Assert that the selected language in dropdown is 'fr'
    language_dropdown = browser.find_element('id', 'id_preferred_language')
    select = Select(language_dropdown)
    assert select.first_selected_option.get_attribute('value') == 'fr'

    # Assert that in the cookies we now have "django_language" with value "fr"
    cookies = browser.get_cookies()
    django_language_cookie = next(
        (cookie for cookie in cookies if cookie['name'] == 'django_language'),
        None
    )
    assert django_language_cookie is not None
    assert django_language_cookie['value'] == 'fr'
#
#
#
# @pytest.mark.selenium
# def test_user_changes_via_quick_preferred_language(browser):
#     pass
