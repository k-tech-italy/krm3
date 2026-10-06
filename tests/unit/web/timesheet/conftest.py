from testutils.factories import ResourceFactory


def resource_client(client):
    resource = ResourceFactory()
    client.login_to_admin(username=resource.user.username, password=resource.user._password)
    return client
