import time
import datetime
import typing

import pytest
from freezegun import freeze_time
from testutils.factories import TaskFactory
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


if typing.TYPE_CHECKING:
    from testutils.selenium import AppTestBrowser


@freeze_time('2025-06-19')
@pytest.mark.selenium
@pytest.mark.django_db
def test_timesheet_quick_add(browser: 'AppTestBrowser', regular_user, resource_factory):
    resource = resource_factory(user=regular_user)

    # Crea un task (usa la funzione per rendere il codice più pulito, ma chiamala qui)
    TaskFactory(
        resource=resource,
        start_date=datetime.date(2025, 6, 1),
        end_date=datetime.date(2025, 6, 30),
    )

    browser.login_as_user(regular_user)
    time.sleep(2) # Considera l'uso di WebDriverWait invece di time.sleep
    browser.click('[href*="/timesheet"]')
    time.sleep(2) # Considera l'uso di WebDriverWait

    # --- Interaction with the specific day element ---
    # Using WebDriverWait for robustness, as elements might not be immediately available
    wait = WebDriverWait(browser.driver, 10) # Wait up to 10 seconds

    # Construct the ID dynamically based on the frozen date
    # Format: "draggable-Day Mon DD YYYY"
    frozen_date = datetime.date(2025, 6, 19)
    # Ensure this format matches exactly what your application generates
    # Example: "Thu Jun 19 2025" or "Wed Feb 14 2024"
    # Python's strftime: %a (short weekday), %b (short month), %d (day), %Y (year)
    # The actual format "Thu Jun 19 2025" implies %a %b %d %Y with no leading zeros for day
    date_part_for_id = frozen_date.strftime('%a %b %d %Y').replace(" 0", " ") # Remove leading zero for day if present
    element_id_prefix = f'draggable-{date_part_for_id}'


    print(f"Attempting to find element with ID starting with: {element_id_prefix}") # Debug print

    try:
        # Wait for the element to be visible and clickable
        element = wait.until(EC.element_to_be_clickable((By.XPATH, f'//div[starts-with(@id, "{element_id_prefix}")]')))
        element.click()
        print("Successfully clicked the draggable element.")
    except Exception as e:
        pytest.fail(f"Could not find or click the draggable element: {e}")
        # Use breakpoint() for interactive debugging if needed
        # breakpoint()


    # After clicking, wait for the form to appear (e.g., check for a form element)
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[name="hours"]')))

    # Inserisci il task (modifica i selettori secondo il tuo form reale)
    # You need to pass 'task_type' into your test function or define it.
    # Assuming task_type is available or a placeholder for now.
    # For a real test, you'd likely fetch/create a task_type or use a known value.
    # For this example, let's assume `task_type` is an object with a `name` attribute.
    # If it's just a string, use: browser.select('select[name="task_type"]', 'Your Task Type Name')

    # Example placeholder for task_type
    # class MockTaskType:
    #     def __init__(self, name):
    #         self.name = name
    # task_type_obj = MockTaskType("Development") # Replace with your actual task type name

    # IMPORTANT: You're selecting by `task_type.name`. Ensure `task_type` is defined/passed or use a hardcoded string
    # For this example, I'll use a placeholder string.
    # If your `testutils.factories.TaskFactory` creates a task and `task_type` is part of it,
    # you might need to pass it into this test or retrieve it.
    # For simplicity, let's assume you want to select an option by its visible text.
    # browser.select('select[name="task_type"]', task_type_obj.name) # If task_type is an object
    browser.fill('input[name="hours"]', '4')
    browser.select('select[name="task_type"]', 'Some Task Type Name') # <-- REPLACE 'Some Task Type Name' with actual option text/value
    browser.click('button[type="submit"]')  # This assumes it's a generic submit button. Be more specific if needed.

    # After saving, wait for the change to reflect or a success message
    today_str_for_assert = frozen_date.strftime('%b %d').replace(" 0", " ") # e.g., "Jun 19"
    print(f"Attempting to assert text '4h' near date: {today_str_for_assert}") # Debug print

    # Verify that the task is present in the UI
    # This XPATH needs to be very precise for your application's structure.
    # It looks for '4h' in a td that is a sibling of a td containing the date.
    # A more robust check might be to find the row for the date, then look within that row.
    try:
        wait.until(EC.text_to_be_present_in_element((By.XPATH, f'//td[contains(text(), "{today_str_for_assert}")]/following-sibling::td'), '4h'))
        print("Successfully asserted '4h' in the timesheet.")
    except Exception as e:
        pytest.fail(f"Assertion failed: '4h' not found in timesheet: {e}")
        # breakpoint()