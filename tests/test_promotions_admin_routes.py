from fastapi.testclient import TestClient

import app.main as main_module


def test_admin_promotion_routes_are_registered_and_admin_only():
    schema = main_module.app.openapi()
    paths = schema["paths"]

    assert "get" in paths.get("/api/v1/admin/promotions", {})
    assert "post" in paths.get("/api/v1/admin/promotions", {})
    assert "patch" in paths.get("/api/v1/admin/promotions/{promotion_id}", {})
    assert "delete" in paths.get("/api/v1/admin/promotions/{promotion_id}", {})

    client = TestClient(main_module.app)
    assert client.get("/api/v1/admin/promotions").status_code in {401, 403}
    assert client.post("/api/v1/admin/promotions", json={"code": "TEST10", "discountValue": 10}).status_code in {
        401,
        403,
    }
    assert client.patch("/api/v1/admin/promotions/1", json={"isActive": False}).status_code in {401, 403}
    assert client.delete("/api/v1/admin/promotions/1").status_code in {401, 403}
