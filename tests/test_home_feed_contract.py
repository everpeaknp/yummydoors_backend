import pytest
from sqlalchemy.dialects import postgresql

import app.db.base  # noqa: F401 - required for SQLAlchemy mapper resolution
from app.modules.catalog.repository import CatalogRepository
from app.modules.restaurants.schemas import HomeFeedFilterOption, HomeFeedResponse, HomeLocationContext


class _ScalarResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class _ExecuteResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return _ScalarResult(self._items)


class _SessionRecorder:
    def __init__(self, result_batches):
        self.result_batches = list(result_batches)
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        return _ExecuteResult(self.result_batches.pop(0))


@pytest.mark.asyncio
async def test_popular_items_are_ranked_by_delivered_sales_before_fallback():
    sales_items = [object()]
    session = _SessionRecorder([sales_items])
    repository = CatalogRepository(session)

    result = await repository.list_popular_items(limit=8)

    assert result == sales_items
    assert len(session.statements) == 1
    compiled = str(
        session.statements[0].compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert "order_items" in compiled
    assert "orders.status = 'delivered'" in compiled
    assert "sum(order_items.quantity)" in compiled
    assert "ORDER BY sum(order_items.quantity) DESC" in compiled


@pytest.mark.asyncio
async def test_popular_items_fall_back_to_manual_popularity_when_no_sales_exist():
    fallback_items = [object()]
    session = _SessionRecorder([[], fallback_items])
    repository = CatalogRepository(session)

    result = await repository.list_popular_items(limit=8)

    assert result == fallback_items
    assert len(session.statements) == 2
    fallback_sql = str(
        session.statements[1].compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert "ORDER BY menu_items.favorite_count DESC" in fallback_sql
    assert "menu_items.popularity_score DESC" in fallback_sql


@pytest.mark.asyncio
async def test_feed_menu_item_queries_eager_load_modifier_groups_for_summary_serialization():
    session = _SessionRecorder([[object()], [object()], [object()]])
    repository = CatalogRepository(session)

    await repository.list_popular_items(limit=8)
    await repository.list_featured_items(limit=8)
    await repository.list_items_by_restaurants([1], limit=8)

    assert len(session.statements) == 3
    for statement in session.statements:
        assert len(statement._with_options) == 1
        option_path = str(statement._with_options[0].path)
        assert "MenuItem.modifier_groups" in option_path
        assert "MenuModifierGroup.items" in option_path


def test_home_feed_exposes_flutter_filter_options():
    feed = HomeFeedResponse(
        location_context=HomeLocationContext(
            location_title="Choose location",
            location_subtitle="Set delivery address",
        ),
        categories=[],
        restaurants=[],
        filters=[
            HomeFeedFilterOption(key="filters", label="Filters", type="sheet"),
            HomeFeedFilterOption(key="sort_by", label="Sort By", type="sort"),
            HomeFeedFilterOption(key="highly_reordered", label="Highly Reordered"),
            HomeFeedFilterOption(key="veg", label="Veg"),
            HomeFeedFilterOption(key="non_veg", label="Non Veg"),
        ],
    )

    assert [item.label for item in feed.filters] == [
        "Filters",
        "Sort By",
        "Highly Reordered",
        "Veg",
        "Non Veg",
    ]
