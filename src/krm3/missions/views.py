import logging

from django.contrib.auth.decorators import permission_required
from django.views.generic import FormView
# from django.shortcuts import render
# from django.urls import reverse
# from django.views.generic import RedirectView
from django.views.generic.base import View

logger = logging.getLogger(__name__)


@permission_required("missions.add_reimbursement")
class ReimburseMissionsView(FormView):
    http_method_names = ['post']
    template_name = ''
    form_class = 'missions.forms.MissionsReimbursementForm'

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.render_to_response(context=1,)
