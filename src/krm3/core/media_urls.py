"""URL configuration for protected media endpoints.

These URLs handle serving private media files via nginx X-Accel-Redirect.
All endpoints require authentication. Permission checks will be added in future phases.
"""

from django.urls import path

from krm3.core.media_views import serve_contract_document, serve_document_file, serve_expense_image

app_name = 'media-auth'

urlpatterns = [
    path('expenses/<int:expense_id>/', serve_expense_image, name='expense-image'),
    path('contracts/<int:contract_id>/', serve_contract_document, name='contract-document'),
    path('documents/<int:document_id>/', serve_document_file, name='document-file'),
]
