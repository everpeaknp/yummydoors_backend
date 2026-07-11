from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import app.db.base  # noqa: F401 - required for SQLAlchemy mapper resolution
from app.modules.messages.repository import MessageRepository


class _FakeScalarResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class _FakeExecuteResult:
    def __init__(self, *, items=None, row=None):
        self._items = items or []
        self._row = row

    def scalars(self):
        return _FakeScalarResult(self._items)

    def one_or_none(self):
        return self._row


class _FakeSession:
    def __init__(self, responses):
        self._responses = list(responses)
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        return self._responses.pop(0)


def _message(message_id: int, created_at: datetime):
    return SimpleNamespace(id=message_id, created_at=created_at)


async def test_get_conversation_page_returns_latest_slice_in_ascending_order():
    now = datetime.now(UTC)
    session = _FakeSession(
        [
            _FakeExecuteResult(
                items=[
                    _message(5, now),
                    _message(4, now - timedelta(minutes=1)),
                    _message(3, now - timedelta(minutes=2)),
                ]
            )
        ]
    )

    repository = MessageRepository(session)
    page, has_more = await repository.get_conversation_page(9, 17, limit=2)

    assert [message.id for message in page] == [4, 5]
    assert has_more is True


async def test_get_conversation_page_uses_before_cursor_for_older_messages():
    now = datetime.now(UTC)
    cursor_message = _message(4, now - timedelta(minutes=1))
    session = _FakeSession(
        [
            _FakeExecuteResult(row=cursor_message),
            _FakeExecuteResult(
                items=[
                    _message(3, now - timedelta(minutes=2)),
                    _message(2, now - timedelta(minutes=3)),
                ]
            ),
        ]
    )

    repository = MessageRepository(session)
    page, has_more = await repository.get_conversation_page(9, 17, limit=2, before_message_id=4)

    assert [message.id for message in page] == [2, 3]
    assert has_more is False


async def test_get_conversation_page_returns_empty_when_cursor_message_is_missing():
    session = _FakeSession([_FakeExecuteResult(row=None)])

    repository = MessageRepository(session)
    page, has_more = await repository.get_conversation_page(9, 17, limit=2, before_message_id=999)

    assert page == []
    assert has_more is False
