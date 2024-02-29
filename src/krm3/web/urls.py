from django.urls import path, include

from .views import HomeView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('missions/', include('krm3.missions.urls'))
]
