from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from krm3.missions.models import Expense, Mission

from .serializers.expense import ExpenseSerializer
from .serializers.mission import MissionSerializer


class MissionAPIViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = MissionSerializer
    queryset = Mission.objects.all()


class ExpenseAPIViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ExpenseSerializer
    queryset = Expense.objects.all()

    @action(
        methods=['post'],
        detail=True, permission_classes=[],
        # parser_classes=(MultiPartParser, FormParser)
    )
    def upload_image(self, request, *args, **kwargs):
        """Upload the image to the mission."""
        expense: Expense = self.get_object()
        expense.image = request.FILES['image']
        expense.save()

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
