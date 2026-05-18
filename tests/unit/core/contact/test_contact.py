from testutils.factories import ContactFactory


def test_fetch_picture(regular_user):
    regular_user.profile.picture = "example_url"
    contact = ContactFactory(user=regular_user)
    contact.fetch_picture()
    assert contact.picture == "example_url"
