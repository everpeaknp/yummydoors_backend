from __future__ import annotations

from collections import defaultdict
from functools import lru_cache

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import settings
from app.modules.auth.schemas import PosLinkStatus, PosRestaurantMatch
from app.modules.integrations.pos.models import ExternalUserLink


@lru_cache
def get_pos_engine() -> AsyncEngine | None:
    if not settings.pos_database_url:
        return None
    return create_async_engine(settings.pos_database_url, future=True, echo=settings.db_echo)


def _normalize_roles(legacy_role: str | None, primary_role: str | None, raw_roles: object) -> list[str]:
    values: list[str] = []
    for candidate in [primary_role, legacy_role]:
        if isinstance(candidate, str) and candidate.strip():
            values.append(candidate.strip())

    if isinstance(raw_roles, list):
        for candidate in raw_roles:
            if isinstance(candidate, str) and candidate.strip():
                values.append(candidate.strip())

    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(value)
    return deduped


async def lookup_pos_link_status(
    *,
    email: str | None,
    external_links: list[ExternalUserLink],
) -> PosLinkStatus:
    engine = get_pos_engine()
    linked_links = [link for link in external_links if link.system_name == "yummy_pos"]
    linked_user_ids = [link.external_user_id for link in linked_links]
    linked_restaurant_ids = [
        link.external_restaurant_id for link in linked_links if link.external_restaurant_id
    ]

    if engine is None:
        return PosLinkStatus(
            enabled=False,
            status="not_configured",
            message="Yummy POS lookup is not configured for this environment.",
            linked_user_ids=linked_user_ids,
            linked_restaurant_ids=linked_restaurant_ids,
        )

    normalized_email = email.strip().lower() if email else None
    if not normalized_email:
        return PosLinkStatus(
            enabled=True,
            status="email_required",
            message="Yummy POS lookup needs an email address because phone-based POS matching is not wired yet.",
            linked_user_ids=linked_user_ids,
            linked_restaurant_ids=linked_restaurant_ids,
        )

    query = text(
        """
        WITH matched_user AS (
            SELECT
                u.id,
                u.name,
                u.email,
                u.role,
                u.roles,
                u.primary_role,
                u.restaurant_id
            FROM users u
            WHERE lower(u.email) = :email
              AND coalesce(u.is_active, true) = true
        ),
        restaurant_sources AS (
            SELECT
                mu.id AS user_id,
                mu.name AS user_name,
                mu.email AS user_email,
                mu.role AS legacy_role,
                mu.roles AS role_list,
                mu.primary_role,
                mu.restaurant_id AS pos_user_restaurant_id,
                mu.restaurant_id AS restaurant_id,
                'direct_restaurant' AS relationship_source,
                false AS is_owner
            FROM matched_user mu
            WHERE mu.restaurant_id IS NOT NULL

            UNION ALL

            SELECT
                mu.id AS user_id,
                mu.name AS user_name,
                mu.email AS user_email,
                mu.role AS legacy_role,
                mu.roles AS role_list,
                mu.primary_role,
                mu.restaurant_id AS pos_user_restaurant_id,
                ra.restaurant_id,
                'restaurant_admin' AS relationship_source,
                ra.is_owner
            FROM matched_user mu
            JOIN restaurant_admins ra
              ON ra.user_id = mu.id

            UNION ALL

            SELECT
                mu.id AS user_id,
                mu.name AS user_name,
                mu.email AS user_email,
                mu.role AS legacy_role,
                mu.roles AS role_list,
                mu.primary_role,
                mu.restaurant_id AS pos_user_restaurant_id,
                r.id AS restaurant_id,
                'registered_by' AS relationship_source,
                true AS is_owner
            FROM matched_user mu
            JOIN restaurant_info r
              ON r.registered_by = mu.id
        )
        SELECT
            rs.user_id,
            rs.user_name,
            rs.user_email,
            rs.legacy_role,
            rs.role_list,
            rs.primary_role,
            rs.pos_user_restaurant_id,
            rs.restaurant_id,
            rs.relationship_source,
            rs.is_owner,
            r.name AS restaurant_name,
            r.phone AS restaurant_phone
        FROM restaurant_sources rs
        LEFT JOIN restaurant_info r
          ON r.id = rs.restaurant_id
        ORDER BY rs.user_id, rs.restaurant_id
        """
    )

    async with engine.connect() as connection:
        rows = (await connection.execute(query, {"email": normalized_email})).mappings().all()

    if not rows:
        return PosLinkStatus(
            enabled=True,
            status="no_match",
            message="No Yummy POS user matched this email address.",
            matched_by=["email"],
            linked_user_ids=linked_user_ids,
            linked_restaurant_ids=linked_restaurant_ids,
        )

    first = rows[0]
    restaurants_by_id: dict[str, dict] = defaultdict(dict)
    for row in rows:
        restaurant_id = row["restaurant_id"]
        if restaurant_id is None:
            continue
        key = str(restaurant_id)
        current = restaurants_by_id.get(key) or {
            "pos_restaurant_id": key,
            "name": row["restaurant_name"] or f"Restaurant {restaurant_id}",
            "phone": row["restaurant_phone"],
            "relationship_sources": [],
            "is_owner": False,
        }
        source = row["relationship_source"]
        if source and source not in current["relationship_sources"]:
            current["relationship_sources"].append(source)
        current["is_owner"] = current["is_owner"] or bool(row["is_owner"])
        restaurants_by_id[key] = current

    matched_restaurants = [
        PosRestaurantMatch(**restaurant)
        for _, restaurant in sorted(restaurants_by_id.items(), key=lambda item: int(item[0]))
    ]
    matched_roles = _normalize_roles(
        legacy_role=first["legacy_role"],
        primary_role=first["primary_role"],
        raw_roles=first["role_list"],
    )

    is_linked = bool(linked_links)
    status = "linked" if is_linked else "match_found"
    if is_linked:
        message = (
            f"Linked to Yummy POS user #{first['user_id']} with "
            f"{len(matched_restaurants)} matched restaurant context(s)."
        )
    else:
        message = (
            f"Found Yummy POS user #{first['user_id']} with "
            f"{len(matched_restaurants)} matched restaurant context(s). Link confirmation is still pending."
        )

    return PosLinkStatus(
        enabled=True,
        status=status,
        message=message,
        matched_by=["email"],
        matched_user_id=str(first["user_id"]),
        matched_user_name=first["user_name"],
        matched_user_email=first["user_email"],
        matched_roles=matched_roles,
        matched_restaurants=matched_restaurants,
        linked_user_ids=linked_user_ids,
        linked_restaurant_ids=linked_restaurant_ids,
    )
