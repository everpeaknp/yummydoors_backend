from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.modules.orders.models import OrderStatus
from app.modules.orders.schemas import MerchantOrderResponse
from app.modules.rider_dispatch.service import RiderDispatchService
from app.modules.orders.service import OrderService


def _role(code: str):
    return SimpleNamespace(role=SimpleNamespace(code=code))


def _assignment(restaurant_id: int, assignment_type: str):
    return SimpleNamespace(
        restaurant_id=restaurant_id,
        assignment_type=assignment_type,
    )


def _rider(*, accepting: bool, assignments=()):
    return SimpleNamespace(
        id=17,
        full_name="Rider One",
        phone=None,
        avatar_url=None,
        is_accepting_offers=accepting,
        rider_work_mode="freelance",
        roles=[_role("rider")],
        restaurant_assignments=list(assignments),
        current_latitude=None,
        current_longitude=None,
    )


def _restaurant():
    return SimpleNamespace(
        id=9,
        latitude=None,
        longitude=None,
    )


def test_offline_freelancer_is_not_an_open_dispatch_candidate():
    service = RiderDispatchService(None)  # type: ignore[arg-type]

    candidate = service._build_candidate(
        _rider(accepting=False),
        _restaurant(),
        None,
    )

    assert candidate is None


def test_offline_private_rider_still_receives_assigned_restaurant_offers():
    service = RiderDispatchService(None)  # type: ignore[arg-type]
    private_assignment = _assignment(9, "rider_private")

    candidate = service._build_candidate(
        _rider(accepting=False, assignments=[private_assignment]),
        _restaurant(),
        None,
    )

    assert candidate is not None
    assert candidate.assignment_type == "rider_private"


def test_preferred_relationship_is_treated_as_preferred_tier():
    service = RiderDispatchService(None)  # type: ignore[arg-type]
    preferred_assignment = _assignment(9, "rider_preferred")

    candidate = service._build_candidate(
        _rider(accepting=True, assignments=[preferred_assignment]),
        _restaurant(),
        None,
    )

    assert candidate is not None
    assert candidate.assignment_type == "rider_preferred"


def test_rider_order_response_exposes_targeted_offer_metadata():
    response = MerchantOrderResponse(
        id=1,
        customerId=2,
        restaurantId=3,
        orderNumber="ORD-1",
        restaurantName="Test restaurant",
        customerName="Customer",
        date="2026-07-12",
        status=OrderStatus.preparing,
        totalPrice=100,
        items=[],
        riderOfferId=9,
        riderOfferTier="manual",
    )

    assert response.riderOfferId == 9
    assert response.riderOfferTier == "manual"


def test_merchant_cannot_mark_rider_assigned_order_delivered():
    service = OrderService(None)  # type: ignore[arg-type]
    order = SimpleNamespace(rider_user_id=17)

    with pytest.raises(HTTPException) as exc:
        service._validate_merchant_delivery(order)

    assert exc.value.status_code == 409


def test_merchant_can_mark_unassigned_order_delivered():
    service = OrderService(None)  # type: ignore[arg-type]

    service._validate_merchant_delivery(SimpleNamespace(rider_user_id=None))
