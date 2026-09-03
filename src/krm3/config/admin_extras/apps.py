"""Admin extras app module."""

import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, TextIO

from django.apps import AppConfig

if TYPE_CHECKING:
    from smart_admin.site import SmartAdminSite

logger = logging.getLogger(__name__)


@contextmanager
def catch_stdout(buff: TextIO) -> Iterator[None]:  # noqa: D103
    stdout = sys.stdout
    sys.stdout = buff
    yield
    sys.stdout = stdout


class AdminConfig(AppConfig):  # noqa: D101
    name = 'krm3.config.admin_extras'
    default = False

    def ready(self) -> None:  # noqa: D102
        super().ready()
        from django.contrib.admin import site  # noqa: PLC0415
        from django.contrib.contenttypes.models import ContentType  # noqa: PLC0415
        from smart_admin.console import panel_migrations, panel_sysinfo  # noqa: PLC0415
        from smart_admin.decorators import smart_register  # noqa: PLC0415
        from smart_admin.smart_auth.admin import (  # noqa: PLC0415
            ContentTypeAdmin,
            Group,
            GroupAdmin,
            Permission,
            PermissionAdmin,
        )

        from krm3.config.admin_extras.panels import panel_converter  # noqa: PLC0415

        from .panels import email, panel_sql, sentry, system_panel  # noqa: PLC0415

        site: SmartAdminSite

        site.register_panel(system_panel)
        site.register_panel(panel_sysinfo)
        site.register_panel(panel_migrations)
        site.register_panel(email)
        site.register_panel(sentry)
        site.register_panel(panel_sql)
        site.register_panel(panel_converter)

        smart_register(Permission)(PermissionAdmin)
        smart_register(Group)(GroupAdmin)
        smart_register(ContentType)(ContentTypeAdmin)
