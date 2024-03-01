from django.urls import include, path

from .views import HomeView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('missions/', include('krm3.missions.urls'))
]
