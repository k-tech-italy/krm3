from django.urls import include, path

from .views import HomeView, AvailabilityReportView

urlpatterns = [
    path('', HomeView.as_view()),
    path('home/', HomeView.as_view(), name='home'),
    path('availability/', AvailabilityReportView.as_view(), name='availability'),
    path('missions/', include('krm3.missions.urls'))
]
