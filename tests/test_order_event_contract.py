"""Locks down the order status/timeline "wire contract" that the desktop and
mobile clients depend on.

Both the desktop (yummydoors_desktop) and mobile (yummy-user) apps hard-code
the set of `status` values and realtime `event`/`event_name` strings they
expect to see over the orders/rider-dispatch WebSocket channels and REST
responses. Nothing enforced that those literals stayed in sync with what the
backend actually emits — a typo or a renamed event here would silently break
client-side status badges/notifications with no test failure anywhere.

These tests make that contract explicit: if a new event name is introduced or
an existing one is renamed, this test fails until the change is deliberate
(the frozen set below is updated), which is also the developer's cue to check
the desktop and mobile clients for the same rename.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.modules.orders.models import OrderStatus

BACKEND_ROOT = Path(__file__).resolve().parent.parent / "app"

# The `order.status` field itself — enforced by the DB enum and the
# merchant-status state machine in orders/service.py.
EXPECTED_ORDER_STATUS_VALUES = {"toPay", "placed", "preparing", "delivered", "cancelled"}

# Finer-grained realtime timeline/notification events emitted alongside (but
# distinct from) `order.status` — e.g. "picked_up" and "rider_assigned" never
# appear as an `order.status` value, only as a WebSocket/push event name.
EXPECTED_ORDER_EVENT_NAMES = {
    "order_update",
    "new_order",
    "rider_assigned",
    "picked_up",
    "delivered",
    "rider_offer",
    "rider_team_invitation",
}

_EVENT_LITERAL_RE = re.compile(r'event(?:_name)?\s*=\s*"([a-z_]+)"')
_EVENT_KEY_LITERAL_RE = re.compile(r'"event"\s*:\s*"([a-z_]+)"')


def _scan_event_literals(*relative_paths: str) -> set[str]:
    found: set[str] = set()
    for relative_path in relative_paths:
        source = (BACKEND_ROOT / relative_path).read_text()
        found.update(_EVENT_LITERAL_RE.findall(source))
        found.update(_EVENT_KEY_LITERAL_RE.findall(source))
    return found


def test_order_status_enum_matches_the_documented_client_contract():
    actual = {member.value for member in OrderStatus}
    assert actual == EXPECTED_ORDER_STATUS_VALUES, (
        "OrderStatus changed without updating the documented client contract "
        "in tests/test_order_event_contract.py — desktop and mobile both hard-code "
        "this status set and need a matching update."
    )


def test_order_and_rider_dispatch_event_names_match_the_documented_client_contract():
    actual = _scan_event_literals(
        "modules/orders/api.py",
        "modules/rider_dispatch/api.py",
        "modules/rider_dispatch/service.py",
    )
    assert actual == EXPECTED_ORDER_EVENT_NAMES, (
        "A realtime order/rider-dispatch event name was added, removed, or renamed "
        "without updating the documented client contract in "
        "tests/test_order_event_contract.py. Check the desktop "
        "(app/(dashboard)/orders, rider, merchant/orders pages) and mobile "
        "(lib/features/orders, lib/features/rider) clients for the same event name."
    )
