from types import SimpleNamespace

import app.main  # noqa: F401 — registers the full SQLAlchemy mapper graph.
from app.modules.catalog.revisions import record_menu_item_revision


class _FakeSession:
    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)


def _item(**overrides):
    defaults = dict(id=1, name="Momo", price=200.0, currency_code="NPR", is_available=True)
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_records_revision_when_price_changes():
    session = _FakeSession()
    item = _item()

    revision = record_menu_item_revision(
        session, item, {"price": 250.0}, changed_by_user_id=7, source="merchant"
    )

    assert revision is not None
    assert session.added == [revision]
    assert revision.previous_values == {"price": 200.0}
    assert revision.new_values == {"price": 250.0}
    assert revision.source == "merchant"
    assert revision.changed_by_user_id == 7


def test_no_revision_when_value_is_unchanged():
    session = _FakeSession()
    item = _item(price=200.0)

    revision = record_menu_item_revision(
        session, item, {"price": 200.0}, changed_by_user_id=7, source="merchant"
    )

    assert revision is None
    assert session.added == []


def test_ignores_untracked_fields():
    session = _FakeSession()
    item = _item()

    revision = record_menu_item_revision(
        session, item, {"description": "new description"}, changed_by_user_id=7, source="admin"
    )

    assert revision is None
    assert session.added == []


def test_only_tracked_fields_that_changed_are_recorded():
    session = _FakeSession()
    item = _item(price=200.0, name="Momo", is_available=True)

    revision = record_menu_item_revision(
        session,
        item,
        {"price": 200.0, "name": "Steam Momo", "is_available": False},
        changed_by_user_id=None,
        source="admin",
    )

    assert revision is not None
    assert set(revision.previous_values.keys()) == {"name", "is_available"}
    assert revision.previous_values == {"name": "Momo", "is_available": True}
    assert revision.new_values == {"name": "Steam Momo", "is_available": False}
