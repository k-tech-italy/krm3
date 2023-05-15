def mission_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return 'missions/expenses/R{0}/M{1}/{2}'.format(instance.mission.resource.id, instance.mission.id, filename)
