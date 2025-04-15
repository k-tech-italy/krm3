import pytest


@pytest.fixture
def basket_factory():
    from factories import BasketFactory

    def _make(**kwargs):
        return BasketFactory(**kwargs)

    return _make


@pytest.fixture
def invoice_entry_factory():
    from factories import InvoiceEntryFactory

    def _make(**kwargs):
        return InvoiceEntryFactory(**kwargs)

    return _make


@pytest.fixture
def task_factory():
    from factories import TaskFactory

    def _make(**kwargs):
        return TaskFactory(**kwargs)

    return _make


@pytest.fixture
def time_entry_factory():
    from factories import TimeEntryFactory

    def _make(**kwargs):
        return TimeEntryFactory(**kwargs)

    return _make
