import typing

if typing.TYPE_CHECKING:
    from krm3.core.models import Mission

EXPENSES_IMAGE_PREFIX = 'missions/expenses'


def mission_directory_path(instance: 'Mission', filename: str) -> str:
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return '{EXPENSES_IMAGE_PREFIX}/R{instance.mission.resource.id}/M{instance.mission.id}/{filename}'
