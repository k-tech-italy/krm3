import logging
from cgi import parse_multipart
from io import BytesIO

from django.core.files.base import ContentFile
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.shortcuts import reverse
from django.template.response import TemplateResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import FormView
from django.views.generic.base import View
from rest_framework.generics import get_object_or_404

from krm3.missions.facilities import ReimbursementFacility
from krm3.missions.forms import MissionsReimbursementForm
from krm3.core.models import Reimbursement, Expense

logger = logging.getLogger(__name__)


class ReimburseMissionsView(FormView):
    form_class = MissionsReimbursementForm
    http_method_names = ['post']
    template_name = 'admin/missions/reimbursement/preview.html'

    def get_context_data(self, **kwargs) -> dict:  # noqa: ANN003
        ret = super().get_context_data(**kwargs)
        ret['resources'] = ReimbursementFacility(ret['form'].cleaned_data['expenses']).render()
        return ret

    def post(self, request, *args, **kwargs):  # noqa: ANN001,ANN002,ANN003,ANN201
        """Instantiate a form instance with the passed POST variables and then check if it's valid."""
        form = self.get_form()
        if form.is_valid():
            url = reverse('missions:reimburse-results')
            ids = form.cleaned_data['expenses']
            reimbursements = ReimbursementFacility(ids).reimburse(
                form.cleaned_data['year'], None, form.cleaned_data['month']
            )
            ids = ','.join([str(r.id) for r in reimbursements])
            return HttpResponseRedirect(f'{url}?ids={ids}')
        return self.form_invalid(form)


class ReimbursementResultsView(View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):  # noqa: ANN001,ANN002,ANN003,ANN201
        ctx = {'reimbursements': Reimbursement.objects.filter(id__in=request.GET['ids'].split(','))}
        return TemplateResponse(request, 'admin/missions/reimbursement/results.html', ctx)


@method_decorator(csrf_exempt, name='dispatch')
class UploadImageView(View):
    http_method_names = ['get', 'patch']

    @staticmethod
    def _validate_otp_and_get_expense(pk: int, otp_value: str) -> Expense | None:
        """
        Validate OTP and return expense if valid, None otherwise.

        Args:
            pk: The expense primary key
            otp_value: The OTP value to validate

        Returns:
            Expense object if OTP is valid, None otherwise

        """
        try:
            expense = get_object_or_404(Expense, pk=pk)
            if expense.check_otp(otp_value):
                return expense
        except Exception:
            logger.exception('Error validating OTP for expense %s', pk)
        return None

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        otp_value = request.GET.get('otp', '')

        expense = self._validate_otp_and_get_expense(pk, otp_value)

        if not expense:
            return HttpResponseBadRequest('Invalid otp.')

        # Build the current URL with query parameters for the login redirect
        current_url = request.get_full_path()

        ctx = {
            'expense': expense,
            'is_authenticated': request.user.is_authenticated,
            'current_url': current_url,
        }
        return TemplateResponse(request, 'admin/missions/mission/upload_image.html', ctx)

    def patch(self, request: HttpRequest, pk: int) -> HttpResponse:
        content_type = request.META.get('CONTENT_TYPE', '')

        if not content_type.startswith('multipart/form-data;'):
            return HttpResponseBadRequest('Invalid Content-Type. Expected multipart/form-data.')

        try:
            # Extract the boundary from the Content-Type header
            boundary_str = content_type.split('boundary=')[-1].strip('"')
            boundary_bytes = boundary_str.encode()
            # Use BytesIO to treat the request body as a file
            environ = {'CONTENT_TYPE': content_type, 'boundary': boundary_bytes}
            form_data = parse_multipart(BytesIO(request.body), environ)

            otp_values = form_data.get('otp', [])
            image_files = form_data.get('image', [])

            otp_value = otp_values[0] if otp_values else ''

            expense = self._validate_otp_and_get_expense(pk, otp_value)

            if not expense:
                return HttpResponseBadRequest('Invalid otp.')

            if not image_files:
                return HttpResponseBadRequest('No image file found in the request.')

            expense.image.save(f'expense{expense.id:09}.png', ContentFile(image_files[0]), save=True)
            return HttpResponse(status=204)

        except Exception as e:
            logger.exception(f'Error parsing multipart data: {e}')
            return HttpResponseBadRequest(f'Failed to parse multipart data: {e}')
