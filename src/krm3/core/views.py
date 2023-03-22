from requests import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken


class BlacklistRefreshView(APIView):
    def post(self, request):
        token = RefreshToken(request.data.get('refresh'))
        token.blacklist()
        return Response()
