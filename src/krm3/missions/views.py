import logging

# from django.shortcuts import render
# from django.urls import reverse
# from django.views.generic import RedirectView
from django.views.generic.base import View

logger = logging.getLogger(__name__)


class ReimburseMissionsView(View):
    http_method_names = ['post']

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return aaa
