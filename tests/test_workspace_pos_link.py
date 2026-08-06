from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import app.main  # noqa: F401 — registers the full SQLAlchemy mapper graph.
from app.modules.integrations.pos.models import RestaurantPosLink
from app.modules.workspaces.service import WorkspaceService


def _request(*, request_type, restaurant_id, pos_restaurant_id=None, status="submitted"):
    return SimpleNamespace(
        id=11,
        request_type=request_type,
        status=status,
        restaurant_id=restaurant_id,
        requested_name="Test Restaurant",
        requested_slug=None,
        city=None,
        area=None,
        latitude=None,
        longitude=None,
        source_system="yummy_pos" if request_type == "pos_link" else "yummydoors",
        pos_restaurant_id=pos_restaurant_id,
        notes=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _application(*, requests):
    return SimpleNamespace(
        id=1,
        user_id=7,
        status="submitted",
        restaurant_requests=requests,
        workspace=SimpleNamespace(
            id=1,
            workspace_type="merchant",
            name="Test Workspace",
            slug="test-workspace",
            status="pending_review",
            primary_restaurant_id=None,
            primary_restaurant=None,
        ),
        admin_notes=None,
        business_name="Test",
        contact_name="Test",
        contact_email=None,
        contact_phone=None,
        notes=None,
        workspace_id=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _make_repository(*, application, existing_pos_link=None):
    repo = SimpleNamespace()
    repo.get_application_by_id = AsyncMock(side_effect=[application, application])
    repo.get_role_by_code = AsyncMock(return_value=SimpleNamespace(id=99))
    repo.get_restaurant_by_id = AsyncMock(
        return_value=SimpleNamespace(id=5, name="Test Restaurant")
    )
    repo.get_restaurant_assignment = AsyncMock(return_value=SimpleNamespace(id=1))
    repo.get_user_role = AsyncMock(return_value=SimpleNamespace(id=1))
    repo.get_restaurant_pos_link = AsyncMock(return_value=existing_pos_link)
    repo.create_restaurant_pos_link = AsyncMock(
        side_effect=lambda link: link,
    )
    repo.get_user_with_workspaces = AsyncMock(return_value=SimpleNamespace(active_restaurant_id=None))
    repo.commit = AsyncMock()
    return repo


@pytest.mark.asyncio
async def test_approving_pos_link_request_creates_restaurant_pos_link():
    request = _request(request_type="pos_link", restaurant_id=5, pos_restaurant_id="POS-42")
    application = _application(requests=[request])
    repo = _make_repository(application=application)

    service = WorkspaceService.__new__(WorkspaceService)
    service.repository = repo

    await service.approve_application(application_id=1, admin_notes=None)

    repo.create_restaurant_pos_link.assert_awaited_once()
    created_link: RestaurantPosLink = repo.create_restaurant_pos_link.call_args.args[0]
    assert created_link.restaurant_id == 5
    assert created_link.pos_restaurant_id == "POS-42"
    assert created_link.is_active is True


@pytest.mark.asyncio
async def test_approving_pos_link_request_skips_existing_link():
    request = _request(request_type="pos_link", restaurant_id=5, pos_restaurant_id="POS-42")
    application = _application(requests=[request])
    existing_link = SimpleNamespace(restaurant_id=5, pos_restaurant_id="POS-42")
    repo = _make_repository(application=application, existing_pos_link=existing_link)

    service = WorkspaceService.__new__(WorkspaceService)
    service.repository = repo

    await service.approve_application(application_id=1, admin_notes=None)

    repo.create_restaurant_pos_link.assert_not_awaited()


@pytest.mark.asyncio
async def test_approving_non_pos_request_does_not_touch_pos_link():
    request = _request(request_type="claim_existing", restaurant_id=5)
    application = _application(requests=[request])
    repo = _make_repository(application=application)

    service = WorkspaceService.__new__(WorkspaceService)
    service.repository = repo

    await service.approve_application(application_id=1, admin_notes=None)

    repo.get_restaurant_pos_link.assert_not_awaited()
    repo.create_restaurant_pos_link.assert_not_awaited()
