from bs4 import BeautifulSoup
from django.urls import reverse
from testutils.factories import ResourceFactory, UserFactory


def test_user_profile_view_with_non_existent_user_id_returns_404(client):
    """Test that accessing a profile with a non-existent user ID returns 404."""
    UserFactory(username='user00', password='pass123')
    client.login(username='user00', password='pass123')

    url = reverse('user_resource', args=[9999])
    response = client.get(url)

    assert response.status_code == 404


def test_user_profile_view_user_without_resource_returns_404(client):
    """Test that accessing a profile for a user without an associated resource returns 404."""
    user = UserFactory(username='user00', password='pass123')
    client.login(username='user00', password='pass123')

    url = reverse('user_resource', args=[user.pk])
    response = client.get(url)

    assert response.status_code == 404


def test_user_profile_view_read_only_mode_for_other_user(client):
    """Test that viewing another user's profile shows read-only view without form or submit button."""
    # Create two users with resources
    viewer = UserFactory(username='viewer', password='pass123')
    ResourceFactory(user=viewer, first_name='ViewerFirst', last_name='ViewerLast')

    other_user = UserFactory(username='otheruser', password='pass456', email='other@example.com')
    other_resource = ResourceFactory(user=other_user, first_name='OtherFirst', last_name='OtherLast')

    # Login as viewer
    client.login(username='viewer', password='pass123')

    # Access other user's profile
    url = reverse('user_resource', args=[other_user.pk])
    response = client.get(url)

    assert response.status_code == 200

    # Parse HTML to verify read-only view
    soup = BeautifulSoup(response.content, 'html.parser')

    # Check that h1 contains the resource's full name
    h1 = soup.find('h1')
    assert h1 is not None
    assert f'{other_resource.first_name} {other_resource.last_name}' in h1.get_text()

    # Check that the paragraph after h1 contains the user's email
    h1_parent = h1.parent
    paragraphs = h1_parent.find_all('p')  # type: ignore
    assert len(paragraphs) > 0
    assert other_user.email in paragraphs[0].get_text()

    # Verify that the form does not exist
    form = soup.find('form', {'class': 'profile-form'})
    assert form is None

    # Verify that first_name and last_name input fields don't exist
    first_name_input = soup.find('input', {'name': 'first_name'})
    last_name_input = soup.find('input', {'name': 'last_name'})
    assert first_name_input is None
    assert last_name_input is None

    # Verify that submit button doesn't exist
    submit_button = soup.find('button', {'type': 'submit'})
    assert submit_button is None

    # Verify that Back button exists
    back_button = soup.find('a', string=lambda text: text and 'Back' in text)  # type: ignore
    assert back_button is not None


def test_user_profile_view_post_to_other_user_resource_returns_403(client):
    """Test that attempting to POST to update another user's resource returns 403 Forbidden."""
    # Create two users with resources
    attacker = UserFactory(username='attacker', password='pass123')
    ResourceFactory(user=attacker, first_name='AttackerFirst', last_name='AttackerLast')

    victim = UserFactory(username='victim', password='pass456')
    victim_resource = ResourceFactory(user=victim, first_name='VictimFirst', last_name='VictimLast')

    # Login as attacker
    client.login(username='attacker', password='pass123')

    # Attempt to POST to victim's profile
    url = reverse('user_resource', args=[victim.pk])
    response = client.post(
        url,
        {
            'first_name': 'HackedFirst',
            'last_name': 'HackedLast',
        },
    )

    # Assert that 403 Forbidden is returned
    assert response.status_code == 403

    # Refresh from database and verify that victim's resource was NOT changed
    victim_resource.refresh_from_db()
    assert victim_resource.first_name == 'VictimFirst'
    assert victim_resource.last_name == 'VictimLast'


def test_user_profile_view_post_with_empty_fields_shows_validation_errors(client):
    """Test that POSTing with empty first_name and last_name shows validation errors."""
    user = UserFactory(username='testuser', password='pass123')
    resource = ResourceFactory(user=user, first_name='OriginalFirst', last_name='OriginalLast')

    client.login(username='testuser', password='pass123')

    url = reverse('user_resource', args=[user.pk])
    response = client.post(
        url,
        {
            'first_name': '',
            'last_name': '',
        },
    )

    assert response.status_code == 200

    # Parse HTML to verify validation errors are displayed
    soup = BeautifulSoup(response.content, 'html.parser')

    # Find error messages for first_name field
    first_name_errors = soup.find_all('span', {'class': 'profile-field-error'})

    # Convert all error text to a single string for easier assertion
    error_texts = [error.get_text() for error in first_name_errors]

    # Assert that validation errors are present
    assert len(error_texts) >= 2, 'Expected at least 2 validation errors (one for each field)'
    assert any('required' in error.lower() for error in error_texts), "Expected 'required' error message"

    # Verify that the resource was NOT updated
    resource.refresh_from_db()
    assert resource.first_name == 'OriginalFirst'
    assert resource.last_name == 'OriginalLast'


def test_user_profile_view_post_with_empty_body_shows_validation_errors(client):
    """Test that POSTing with an empty body (no data) shows validation errors."""
    user = UserFactory(username='testuser', password='pass123')
    resource = ResourceFactory(user=user, first_name='OriginalFirst', last_name='OriginalLast')

    client.login(username='testuser', password='pass123')

    url = reverse('user_resource', args=[user.pk])
    response = client.post(url, {})

    assert response.status_code == 200

    # Parse HTML to verify validation errors are displayed
    soup = BeautifulSoup(response.content, 'html.parser')

    # Find all error messages
    error_spans = soup.find_all('span', {'class': 'profile-field-error'})

    # Convert all error text to a list
    error_texts = [error.get_text() for error in error_spans]

    # Assert that validation errors are present for both required fields
    assert len(error_texts) >= 2, 'Expected at least 2 validation errors (one for each required field)'
    assert any('required' in error.lower() for error in error_texts), "Expected 'required' error message"

    # Verify that the resource was NOT updated
    resource.refresh_from_db()
    assert resource.first_name == 'OriginalFirst'
    assert resource.last_name == 'OriginalLast'


def test_user_profile_view_get_shows_prepopulated_fields(client):
    """Test that GET request shows form fields prepopulated with current user/resource data."""
    user = UserFactory(username='testuser', password='pass123', email='test@example.com')
    ResourceFactory(user=user, first_name='TestFirst', last_name='TestLast')

    client.login(username='testuser', password='pass123')

    url = reverse('user_resource', args=[user.pk])
    response = client.get(url)

    assert response.status_code == 200

    # Parse HTML to check prepopulated field values
    soup = BeautifulSoup(response.content, 'html.parser')

    first_name_field = soup.find('input', {'name': 'first_name'})
    last_name_field = soup.find('input', {'name': 'last_name'})

    # Assert that fields exists
    assert first_name_field is not None
    assert last_name_field is not None

    # Assert that fields are prepopulated with correct values
    assert first_name_field['value'] == 'TestFirst'
    assert last_name_field['value'] == 'TestLast'


def test_user_profile_view_post_updates_all_fields(client):
    """Test that POSTing to the profile view updates all four fields."""
    user = UserFactory(username='oldusername', password='pass123', email='old@example.com')
    resource = ResourceFactory(user=user, first_name='OldFirstName', last_name='OldLastName')

    client.login(username='oldusername', password='pass123')

    url = reverse('user_resource', args=[user.pk])
    response = client.post(
        url,
        {
            'first_name': 'NewFirstName',
            'last_name': 'NewLastName',
        },
    )

    assert response.status_code == 200
    content = response.content.decode()

    # Assert success message is in the response
    assert 'Profile updated successfully' in content

    # Refresh from database to get updated values
    resource.refresh_from_db()

    # Assert all fields were updated
    assert resource.first_name == 'NewFirstName'
    assert resource.last_name == 'NewLastName'


def test_user_profile_view_displays_profile_picture_and_qr_code(client):
    """Test that profile picture and QR code are displayed when user has UserProfile with picture and Resource with
    vcard."""
    user = UserFactory(username='userwitpic', password='pass123', email='withpic@example.com')
    picture_url = 'http://www.example.com/picture.jpg'

    # Get the automatically created profile and update it
    user_profile = user.profile
    user_profile.picture = picture_url
    user_profile.save()

    # VCARD V3 example
    vcard_text = """
        BEGIN:VCARD
        VERSION:3.0
        FN:John Doe
        N:Doe;John;;;
        EMAIL:john.doe@example.com
        TEL:+1234567890
        END:VCARD
    """

    ResourceFactory(user=user, profile=user_profile, first_name='John', last_name='Doe', vcard_text=vcard_text)

    client.login(username='userwitpic', password='pass123')

    url = reverse('user_resource', args=[user.pk])
    response = client.get(url)

    assert response.status_code == 200

    # Parse HTML to check for profile picture and QR code
    soup = BeautifulSoup(response.content, 'html.parser')

    # Find the img tag with class 'profile-picture'
    profile_picture_img = soup.find('img', {'class': 'profile-picture'})

    # Assert the img tag exists
    assert profile_picture_img is not None

    # Assert the src attribute contains the picture URL
    assert profile_picture_img['src'] == picture_url

    # Find the QR code wrapper div
    qr_wrapper = soup.find('div', {'class': 'profile-qr-wrapper'})

    # Assert the QR code wrapper exists
    assert qr_wrapper is not None

    # Find the QR code image container
    qr_image_div = soup.find('div', {'class': 'profile-qr-image'})

    # Assert the QR code image container exists
    assert qr_image_div is not None
