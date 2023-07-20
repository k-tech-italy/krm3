import json

from factories import ExpenseFactory, PaymentCategoryFactory, ExpenseCategoryFactory


def prepare():
    from krm3.missions.models import Mission, Expense
    from krm3.core.models import City, Project, Resource, Country
    from krm3.currencies.models import Currency

    from krm3.missions.impexp.export import MissionExporter
    from krm3.missions.impexp.imp import MissionImporter
    assert Mission.objects.count() == 0

    original_mission = ExpenseFactory().mission
    expense = ExpenseFactory(mission=original_mission)

    payment_type = PaymentCategoryFactory(parent=expense.payment_type)
    category = ExpenseCategoryFactory(parent=expense.category)
    ExpenseFactory(mission=original_mission, payment_type=payment_type, category=category)
    assert Mission.objects.count() == 1
    assert Expense.objects.count() == 3

    pathname = MissionExporter(Mission.objects.all()).export()
    data = MissionImporter.get_data(pathname)

    assert len(data['clients']) == 1
    assert len(data['countries']) == 1
    assert len(data['projects']) == 1
    assert len(data['cities']) == 1
    assert len(data['categories']) == 3
    assert len(data['payment_types']) == 3
    assert len(data['missions']) == 1
    assert len(data['expenses']) == 3

    data_str = json.dumps(data)
    assert data_str.count('EXISTS') == 17
    assert data_str.count('ADD') == 0
    assert data_str.count('AMEND') == 0

    return data, pathname


def test_mission_full_expimp(db):
    from krm3.missions.models import Mission, Expense
    from krm3.core.models import City, Project, Resource, Country
    from krm3.currencies.models import Currency

    from krm3.missions.impexp.imp import MissionImporter

    data, pathname = prepare()
    data_str = json.dumps(data)

    Expense.objects.all().delete()
    Mission.objects.all().delete()
    Resource.objects.all().delete()
    City.objects.all().delete()
    Country.objects.all().delete()
    Project.objects.all().delete()
    Currency.objects.all().delete()

    assert Mission.objects.count() == 0
    assert Expense.objects.count() == 0
    assert City.objects.count() == 0
    assert Country.objects.count() == 0
    assert Project.objects.count() == 0
    assert Currency.objects.count() == 0

    data = MissionImporter.get_data(pathname)

    print(1)
