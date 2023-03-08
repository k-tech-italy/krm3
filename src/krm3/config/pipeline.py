from django.contrib import messages
from django.shortcuts import redirect


def auth_allowed(backend, details, response, request, *args, **kwargs):
    if not backend.auth_allowed(response, details):
        messages.error(request, 'Please Login with the Organization Account')
        return redirect('login')
