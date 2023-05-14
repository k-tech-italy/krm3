from krm3.missions.forms import MissionAdminForm


def test_auto_mission_number(db):
    from factories import MissionFactory
    mission = MissionFactory()
    base = {
        'project': mission.project,
        'city': mission.city,
        'resource': mission.resource,
        'from_date': mission.from_date,
        'to_date': mission.to_date,
    }
    form = MissionAdminForm(base)
    assert form.is_valid()
    assert form.cleaned_data['number'] == 2, 'Should have assigned 2 to 2nd mission in year'

    form = MissionAdminForm(base | {
        'from_date': '2000-01-01',
        'to_date': '2000-01-01',
    })
    assert form.is_valid()
    assert form.cleaned_data['number'] == 1, 'Should have assigned 1 to empty year'
