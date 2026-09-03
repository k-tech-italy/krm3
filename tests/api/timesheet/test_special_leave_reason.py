import pytest
from rest_framework import status
from rest_framework.reverse import reverse

from testutils.date_utils import _dt
from testutils.factories import SpecialLeaveReasonFactory


class TestSpecialLeaveReasonViewSet:
    @staticmethod
    def url():
        return reverse('timesheet-api:api-special-leave-reason-list')

    def test_returns_valid_reasons_in_limited_interval(self, admin_user, api_client):
        interval_start = _dt('2024-01-01')
        interval_end = _dt('2024-01-31')

        # this one is obvious
        always_valid = SpecialLeaveReasonFactory(title='always')
        # starts before our interval's start and doesn't end? it's ok
        valid_since_earlier_date = SpecialLeaveReasonFactory(title='since 1990', from_date=_dt('1900-01-01'))
        # this validity period fully contains our interval, so it's valid
        encompassing_interval = SpecialLeaveReasonFactory(
            title='definitely valid', from_date=_dt('2010-01-01'), to_date=_dt('2030-01-01')
        )
        # on the other hand, we don't want this one, as we can accept
        # the reason only in a part of our interval
        _fully_contained_within_interval = SpecialLeaveReasonFactory(
            title='contained', from_date=_dt('2024-01-10'), to_date=_dt('2024-01-15')
        )
        # not expired yet, still good
        valid_until_future_date = SpecialLeaveReasonFactory(title='until 2030', to_date=_dt('2030-01-01'))
        # not started, we don't want it
        _not_valid_yet = SpecialLeaveReasonFactory(title='not valid yet', from_date=_dt('2027-01-01'))
        # throw it away, it's long expired
        _expired = SpecialLeaveReasonFactory(title='stale and moldy', to_date=_dt('2018-01-01'))
        # partial overlap, we don't want it - see above
        _expiring_within_interval = SpecialLeaveReasonFactory(title='expiring', to_date=_dt('2024-01-05'))
        _starting_within_interval = SpecialLeaveReasonFactory(title='starting', from_date=_dt('2024-01-25'))

        response = api_client(user=admin_user).get(
            self.url(), data={'from': interval_start.isoformat(), 'to': interval_end.isoformat()}
        )
        assert response.status_code == status.HTTP_200_OK
        returned_ids = [item.get('id') for item in response.json()]
        assert returned_ids == [
            always_valid.id,
            valid_since_earlier_date.id,
            encompassing_interval.id,
            valid_until_future_date.id,
        ]

    def test_returns_all_reasons_if_no_interval_provided(self, admin_user, api_client):
        always_valid = SpecialLeaveReasonFactory(title='always')
        with_start_date = SpecialLeaveReasonFactory(title='since 1990', from_date=_dt('1900-01-01'))
        with_end_date = SpecialLeaveReasonFactory(title='until 2030', to_date=_dt('2030-01-01'))
        limited_validity_period = SpecialLeaveReasonFactory(
            title='definitely valid', from_date=_dt('2010-01-01'), to_date=_dt('2030-01-01')
        )

        response = api_client(user=admin_user).get(self.url())
        assert response.status_code == status.HTTP_200_OK
        returned_ids = [item.get('id') for item in response.json()]
        assert returned_ids == [
            always_valid.id,
            with_start_date.id,
            with_end_date.id,
            limited_validity_period.id,
        ]

    @pytest.mark.parametrize('query_param', ('from', 'to'))
    def test_rejects_requests_with_only_one_of_from_and_to(self, query_param, admin_user, api_client):
        SpecialLeaveReasonFactory(title='should not be returned')
        response = api_client(user=admin_user).get(self.url(), data={query_param: '2024-01-01'})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
