from fastapi.testclient import TestClient

import app.main as main_module


def test_rider_review_routes_are_registered_and_auth_gated():
    schema = main_module.app.openapi()
    paths = schema["paths"]

    assert "get" in paths.get("/api/v1/orders/{order_id}/rider-review/eligibility", {})
    assert "post" in paths.get("/api/v1/orders/{order_id}/rider-review", {})
    assert "get" in paths.get("/api/v1/riders/{rider_user_id}/reviews", {})
    assert "get" in paths.get("/api/v1/riders/{rider_user_id}/rating-summary", {})

    client = TestClient(main_module.app)
    assert client.get("/api/v1/orders/1/rider-review/eligibility").status_code in {401, 403}
    assert client.post("/api/v1/orders/1/rider-review", json={"rating": 5}).status_code in {401, 403}
    assert client.get("/api/v1/riders/1/reviews").status_code in {401, 403}
    assert client.get("/api/v1/riders/1/rating-summary").status_code in {401, 403}


def test_admin_rider_review_moderation_routes_are_registered_and_admin_only():
    schema = main_module.app.openapi()
    paths = schema["paths"]

    assert "get" in paths.get("/api/v1/admin/rider-reviews", {})
    assert "patch" in paths.get("/api/v1/admin/rider-reviews/{review_id}/moderation", {})
    assert "delete" in paths.get("/api/v1/admin/rider-reviews/{review_id}", {})

    client = TestClient(main_module.app)
    assert client.get("/api/v1/admin/rider-reviews").status_code in {401, 403}
    assert client.patch("/api/v1/admin/rider-reviews/1/moderation", json={"isPublished": False}).status_code in {
        401,
        403,
    }
    assert client.delete("/api/v1/admin/rider-reviews/1").status_code in {401, 403}
