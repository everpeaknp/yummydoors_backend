from fastapi.testclient import TestClient

import app.main as main_module
from app.modules.admin.dashboard_service import AdminDashboardSummary


def test_dashboard_summary_endpoint_is_registered_and_rejects_unauthenticated_requests():
    schema = main_module.app.openapi()
    assert "get" in schema["paths"].get("/api/v1/admin/dashboard/summary", {}), (
        "GET /admin/dashboard/summary route is not registered"
    )

    client = TestClient(main_module.app)
    response = client.get("/api/v1/admin/dashboard/summary")
    # No auth header supplied — an admin-only KPI endpoint must not serve data
    # to anonymous callers.
    assert response.status_code in {401, 403}


def test_admin_dashboard_summary_schema_shape():
    summary = AdminDashboardSummary(
        orders_today=3,
        orders_this_week=20,
        revenue_today=1500.0,
        revenue_this_week=9000.0,
        active_restaurants=5,
        total_restaurants=8,
        pending_merchant_applications=1,
        pending_rider_applications=2,
        orders_in_flight=4,
        cancelled_orders_this_week=1,
    )
    assert summary.orders_today == 3
    assert summary.revenue_this_week == 9000.0
