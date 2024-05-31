from django.urls import path

from .views import ReimbursementResultsView, ReimburseMissionsView

app_name = 'missions'

urlpatterns = [
    path('reimburse_expenses', ReimburseMissionsView.as_view(), name='reimburse-expenses'),
    path('reimburse_results', ReimbursementResultsView.as_view(), name='reimburse-results'),
]
