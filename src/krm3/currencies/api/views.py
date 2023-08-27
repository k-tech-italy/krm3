from typing import Optional

from django.conf import settings
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from ..models import Rate
from .serializers import RateSerializer


class RateAPIViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = RateSerializer
    queryset = Rate.objects.all()

    @action(
        detail=True,
        permission_classes=[],
        url_path=r'convert/(?P<from_cur>[A-Z]{3})/(?P<amount>(-)?[\d]+(\.\d+)?)'
    )
    def convert_to_base(self, request, pk, from_cur: str, amount):
        """Convert the amount.


        """
        to_cur = settings.CURRENCY_BASE
        converted = Rate.for_date(pk, include=[from_cur, to_cur]).convert(from_value=amount, from_currency=from_cur,
                                                                          to_currency=to_cur)
        return Response(status=200, data=converted)

    @action(
        detail=True,
        permission_classes=[],
        url_path=r'convert/(?P<from_cur>[A-Z]{3})/(?P<amount>(-)?[\d]+(\.\d+)?)/(?P<to_cur>[A-Z]{3})'
    )
    def convert(self, request, pk, from_cur: str, amount, to_cur: Optional[str] = None):
        """Convert the amount.


        """
        converted = Rate.for_date(pk, include=[from_cur, to_cur]).convert(from_value=amount, from_currency=from_cur,
                                                                          to_currency=to_cur)
        return Response(status=200, data=converted)