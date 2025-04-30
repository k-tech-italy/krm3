from __future__ import annotations

from krm3.core.models import Mission


def map_mission_status(status: str) -> Mission.MissionStatus:
    return {
        'S': Mission.MissionStatus.SUBMITTED,
        'D': Mission.MissionStatus.DRAFT,
        'C': Mission.MissionStatus.CANCELLED,
    }[status]
