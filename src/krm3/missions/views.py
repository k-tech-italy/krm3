import logging

from django.http import HttpResponseRedirect
from django.shortcuts import reverse
from django.template.response import TemplateResponse
from django.views.generic import FormView
from django.views.generic.base import View

from krm3.missions.facilities import ReimbursementFacility
from krm3.missions.forms import MissionsReimbursementForm
from krm3.missions.models import Reimbursement

logger = logging.getLogger(__name__)


class ReimburseMissionsView(FormView):
    form_class = MissionsReimbursementForm
    http_method_names = ['post']
    template_name = 'admin/missions/reimbursement/preview.html'

    def get_context_data(self, **kwargs):
        ret = super().get_context_data(**kwargs)
        ret['resources'] = ReimbursementFacility(ret['form'].cleaned_data['expenses']).render()
        return ret

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests: instantiate a form instance with the passed
        POST variables and then check if it's valid.
        """
        form = self.get_form()
        if form.is_valid():
            url = reverse('missions:reimburse-results')
            ids = form.cleaned_data['expenses']
            reimbursements = ReimbursementFacility(ids).reimburse(form.cleaned_data['year'], form.cleaned_data['title'])
            ids = ','.join([str(r.id) for r in reimbursements])
            return HttpResponseRedirect(f'{url}?ids={ids}')
        else:
            return self.form_invalid(form)


class ReimbursementResultsView(View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        ctx = {
            'reimbursements': Reimbursement.objects.filter(id__in=request.GET['ids'].split(','))
        }
        return TemplateResponse(
            request,
            'admin/missions/reimbursement/results.html',
            ctx
        )
