from django.urls import include, path

from .views import HomeView, ExampleView

urlpatterns = [
    path('example/', ExampleView.as_view(), name='home'),
    path('', HomeView.as_view()),
    path('home/', HomeView.as_view(), name='home'),
    path('missions/', include('krm3.missions.urls'))

]
