from fastapi.testclient import TestClient

import app.main as main_module


def test_merchant_promotion_routes_are_registered_and_auth_gated():
    schema = main_module.app.openapi()
    paths = schema["paths"]

    assert "get" in paths.get("/api/v1/merchant/promotions", {})
    assert "post" in paths.get("/api/v1/merchant/promotions", {})
    assert "patch" in paths.get("/api/v1/merchant/promotions/{promotion_id}", {})
    assert "delete" in paths.get("/api/v1/merchant/promotions/{promotion_id}", {})

    # No restaurantId field on the merchant create schema -- it's derived
    # server-side from the merchant's own active workspace, never accepted
    # as client input.
    create_schema = schema["components"]["schemas"]["MerchantPromotionCreateRequest"]
    assert "restaurantId" not in create_schema.get("properties", {})

    client = TestClient(main_module.app)
    assert client.get("/api/v1/merchant/promotions").status_code in {401, 403}
    assert client.post("/api/v1/merchant/promotions", json={"code": "TEST10", "discountValue": 10}).status_code in {
        401,
        403,
    }
    assert client.patch("/api/v1/merchant/promotions/1", json={"isActive": False}).status_code in {401, 403}
    assert client.delete("/api/v1/merchant/promotions/1").status_code in {401, 403}
