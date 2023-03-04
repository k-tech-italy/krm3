from django.conf import settings
from pyoxr import OXRClient, init

if oerai := settings.OPEN_EXCHANGE_RATES_APP_ID:
    init(settings.OPEN_EXCHANGE_RATES_APP_ID)


def get_client():
    return OXRClient(settings.OPEN_EXCHANGE_RATES_APP_ID)
