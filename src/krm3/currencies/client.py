from django.conf import settings
from pyoxr import OXRClient, init


def get_client() -> OXRClient:
    if oerai := settings.OPEN_EXCHANGE_RATES_APP_ID:
        init(oerai)
    return OXRClient(settings.OPEN_EXCHANGE_RATES_APP_ID)
