from django.urls import path

from .views import ReimburseMissionsView

app_name = 'missions'

urlpatterns = [
    path('reimburse_missions', ReimburseMissionsView.as_view(), name='reimburse-mission'),
]
