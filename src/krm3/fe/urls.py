from pathlib import Path

from django.urls import re_path
from .views import serve

import krm3

ROOT=(Path(krm3.fe.__file__).parent / 'static').absolute()

urlpatterns = [
    re_path(
        r'^.*', serve, kwargs={'document_root': ROOT})
]
