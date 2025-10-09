import typing

if typing.TYPE_CHECKING:
    from krm3.core.models import Mission, Contract

EXPENSES_IMAGE_PREFIX = 'missions/expenses'
CONTRACT_DOCUMENT_PREFIX = 'contracts/documents'


def mission_directory_path(instance: 'Mission', filename: str) -> str:
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return '{EXPENSES_IMAGE_PREFIX}/R{instance.mission.resource.id}/M{instance.mission.id}/{filename}'


def contract_directory_path(instance: 'Contract', filename: str) -> str:
    # file will be uploaded to MEDIA_ROOT/contracts/documents/R<resource_id>/C<contract_id>/<filename>
    return f'{CONTRACT_DOCUMENT_PREFIX}/R{instance.resource.id}/C{instance.id}/{filename}'
