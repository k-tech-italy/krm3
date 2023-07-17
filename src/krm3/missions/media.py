EXPENSES_IMAGE_PREFIX = 'missions/expenses'


def mission_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return '{0}/R{1}/M{2}/{3}'.format(
        EXPENSES_IMAGE_PREFIX,
        instance.mission.resource.id, instance.mission.id, filename)
