from fastapi.testclient import TestClient

import app.main as main_module


def test_rider_payroll_routes_are_registered_and_auth_gated():
    schema = main_module.app.openapi()
    paths = schema["paths"]

    assert "get" in paths.get("/api/v1/riders/me/payroll", {})
    assert "patch" in paths.get("/api/v1/admin/riders/{rider_user_id}/salary", {})
    assert "get" in paths.get("/api/v1/admin/rider-salaries", {})
    assert "get" in paths.get("/api/v1/admin/rider-payroll", {})
    assert "post" in paths.get("/api/v1/admin/rider-payroll/{payment_id}/mark-paid", {})

    client = TestClient(main_module.app)
    assert client.get("/api/v1/riders/me/payroll").status_code in {401, 403}
    assert client.patch("/api/v1/admin/riders/1/salary", json={"monthlyAmount": 15000}).status_code in {401, 403}
    assert client.get("/api/v1/admin/rider-salaries").status_code in {401, 403}
    assert client.get("/api/v1/admin/rider-payroll").status_code in {401, 403}
    assert client.post("/api/v1/admin/rider-payroll/1/mark-paid").status_code in {401, 403}


def test_wallet_and_old_payout_routes_are_gone():
    schema = main_module.app.openapi()
    paths = schema["paths"]

    assert "/api/v1/riders/me/wallet" not in paths
    assert "/api/v1/admin/rider-wallets" not in paths
    assert "/api/v1/riders/me/payouts" not in paths
    assert "/api/v1/admin/rider-payouts" not in paths
