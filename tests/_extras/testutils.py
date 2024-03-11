from krm3.missions.models import Mission


def map_mission_status(status: str) -> 'Mission.MissionStatus':
    from krm3.missions.models import Mission
    return {
        'S': Mission.MissionStatus.SUBMITTED,
        'D': Mission.MissionStatus.DRAFT,
        'C': Mission.MissionStatus.CANCELLED
    }[status]
