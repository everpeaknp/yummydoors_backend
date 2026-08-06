from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import MenuItem, MenuItemRevision

# Only these fields are worth an audit trail entry — the ones that affect
# what a customer sees or pays. Cosmetic fields (description, image_url,
# is_featured, etc.) aren't tracked to keep the history focused.
TRACKED_FIELDS = {"price", "currency_code", "is_available", "name"}


def record_menu_item_revision(
    session: AsyncSession,
    item: MenuItem,
    incoming: dict[str, Any],
    *,
    changed_by_user_id: int | None,
    source: str,
) -> MenuItemRevision | None:
    """Diffs `incoming` against `item`'s current values for the tracked
    fields and, if anything actually changed, adds a MenuItemRevision row.

    Must be called BEFORE the incoming values are applied to `item`, since it
    reads `item`'s current state as the "previous" snapshot. Returns None
    (and adds nothing) if none of the tracked fields are present in
    `incoming` or none of them differ from the current value.
    """
    previous_values: dict[str, Any] = {}
    new_values: dict[str, Any] = {}
    for field in TRACKED_FIELDS:
        if field not in incoming:
            continue
        current = getattr(item, field, None)
        proposed = incoming[field]
        if current != proposed:
            previous_values[field] = current
            new_values[field] = proposed

    if not previous_values:
        return None

    revision = MenuItemRevision(
        menu_item_id=item.id,
        changed_by_user_id=changed_by_user_id,
        source=source,
        previous_values=previous_values,
        new_values=new_values,
    )
    session.add(revision)
    return revision
