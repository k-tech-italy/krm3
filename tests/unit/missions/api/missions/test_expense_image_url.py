"""Expense images are private media: the API must expose their authenticated URL (taiga#575)."""

import pytest
from rest_framework.reverse import reverse
from testutils.factories import ExpenseFactory


def _image_url(expense):
    return f'http://testserver{reverse("media-auth:expense-image", args=[expense.pk])}'


def _expense_data(response, url_name, expense):
    data = response.json()
    if url_name == 'missions-api:expense-list':
        return next(item for item in data['results'] if item['id'] == expense.pk)
    if url_name == 'missions-api:expense-detail':
        return data
    mission = next(item for item in data['results'] if item['id'] == expense.mission_id) if 'results' in data else data
    return next(item for item in mission['expenses'] if item['id'] == expense.pk)


@pytest.mark.parametrize(
    ('url_name', 'by_pk'),
    [
        pytest.param('missions-api:expense-list', None, id='expense-list'),
        pytest.param('missions-api:expense-detail', 'expense', id='expense-detail'),
        pytest.param('missions-api:mission-list', None, id='mission-list'),
        pytest.param('missions-api:mission-detail', 'mission', id='mission-detail'),
    ],
)
@pytest.mark.parametrize('with_image', [pytest.param(True, id='with-image'), pytest.param(False, id='without-image')])
def test_api_exposes_authenticated_image_url(
    api_client, admin_user, private_media, expense_image, url_name, by_pk, with_image
):
    expense = ExpenseFactory(image=expense_image if with_image else None)
    args = {'expense': [expense.pk], 'mission': [expense.mission_id], None: []}[by_pk]

    response = api_client(user=admin_user).get(reverse(url_name, args=args))

    assert response.status_code == 200
    assert _expense_data(response, url_name, expense)['image'] == (_image_url(expense) if with_image else None)
