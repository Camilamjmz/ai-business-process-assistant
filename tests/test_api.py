from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_all_analytics_routes_return_json_successfully() -> None:
    routes = [
        "/api/sales/summary", "/api/sales/top-products?limit=3", "/api/sales/trend",
        "/api/sales/compare?period_a_start=2025-01-01&period_a_end=2025-01-31&period_b_start=2025-02-01&period_b_end=2025-02-28",
        "/api/products/PRD-001/sales", "/api/inventory", "/api/inventory/summary",
        "/api/inventory/low-stock", "/api/inventory/reorder-recommendations?limit=3",
        "/api/suppliers", "/api/suppliers/SUP-001",
    ]
    for route in routes:
        response = client.get(route)
        assert response.status_code == 200, (route, response.text)
        assert response.headers["content-type"].startswith("application/json")


def test_api_unknown_ids_return_404() -> None:
    assert client.get("/api/products/PRD-999/sales").status_code == 404
    assert client.get("/api/suppliers/SUP-999").status_code == 404


def test_api_rejects_invalid_ranges_and_limits() -> None:
    response = client.get("/api/sales/summary?start_date=2025-03-01&end_date=2025-02-01")
    assert response.status_code == 400
    assert "start_date" in response.json()["detail"]
    assert client.get("/api/sales/top-products?limit=0").status_code == 422
    assert client.get("/api/inventory/reorder-recommendations?limit=0").status_code == 422
    assert client.get("/api/sales/summary?start_date=not-a-date").status_code == 422
    assert client.get("/api/sales/trend?granularity=weekly").status_code == 422
