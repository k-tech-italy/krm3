import pytest
from click.exceptions import Exit
from django.core.management import call_command
from flags.models import FlagState
from flags.state import flag_enabled


@pytest.mark.django_db
class TestAddFlag:
    def test_adds_condition(self) -> None:
        call_command('add_flag', 'MISSIONS_ENABLED', 'parameter', 'missions', '--required')
        state = FlagState.objects.get(name='MISSIONS_ENABLED')
        assert (state.condition, state.value, state.required) == ('parameter', 'missions', True)

    def test_not_required_by_default(self) -> None:
        call_command('add_flag', 'MISSIONS_ENABLED', 'boolean', 'True')
        assert FlagState.objects.get(name='MISSIONS_ENABLED').required is False
        assert flag_enabled('MISSIONS_ENABLED')

    def test_existing_condition_updates_required(self) -> None:
        call_command('add_flag', 'MISSIONS_ENABLED', 'boolean', 'True', '--required')
        call_command('add_flag', 'MISSIONS_ENABLED', 'boolean', 'True')
        state = FlagState.objects.get(name='MISSIONS_ENABLED')
        assert state.required is False

    @pytest.mark.parametrize(
        'args',
        [
            pytest.param(['NOT_A_FLAG', 'boolean', 'True'], id='unknown-flag'),
            pytest.param(['MISSIONS_ENABLED', 'not_a_condition', 'x'], id='unknown-condition'),
            pytest.param(['MISSIONS_ENABLED', 'boolean', 'maybe'], id='invalid-value'),
        ],
    )
    def test_invalid_input(self, args: list[str], capsys: pytest.CaptureFixture) -> None:
        with pytest.raises(Exit):
            call_command('add_flag', *args)
        assert 'CommandError' in capsys.readouterr().err
        assert not FlagState.objects.exists()


@pytest.mark.django_db
class TestDeleteFlag:
    def test_deletes_matching_condition_only(self) -> None:
        FlagState.objects.create(name='MISSIONS_ENABLED', condition='boolean', value='True')
        FlagState.objects.create(name='MISSIONS_ENABLED', condition='parameter', value='missions')
        call_command('delete_flag', 'MISSIONS_ENABLED', 'boolean', 'True')
        assert list(FlagState.objects.values_list('condition', flat=True)) == ['parameter']

    def test_missing_condition(self) -> None:
        with pytest.raises(Exit):
            call_command('delete_flag', 'MISSIONS_ENABLED', 'boolean', 'True')
