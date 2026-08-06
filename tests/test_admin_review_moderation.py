from fastapi.testclient import TestClient

import app.main as main_module


def test_review_moderation_routes_are_registered_and_admin_only():
    schema = main_module.app.openapi()
    paths = schema["paths"]

    assert "get" in paths.get("/api/v1/admin/reviews", {})
    assert "patch" in paths.get("/api/v1/admin/reviews/{review_id}/moderation", {})
    assert "delete" in paths.get("/api/v1/admin/reviews/{review_id}", {})

    client = TestClient(main_module.app)
    assert client.get("/api/v1/admin/reviews").status_code in {401, 403}
    assert client.patch("/api/v1/admin/reviews/1/moderation", json={"is_published": False}).status_code in {
        401,
        403,
    }
    assert client.delete("/api/v1/admin/reviews/1").status_code in {401, 403}


def test_menu_item_revisions_route_is_registered_and_admin_only():
    schema = main_module.app.openapi()
    paths = schema["paths"]

    assert "get" in paths.get("/api/v1/admin/menu-items/{menu_item_id}/revisions", {})

    client = TestClient(main_module.app)
    assert client.get("/api/v1/admin/menu-items/1/revisions").status_code in {401, 403}
