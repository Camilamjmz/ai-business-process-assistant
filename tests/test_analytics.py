import math

import pytest

from app.tools.inventory import (
    classify_inventory_status,
    get_inventory_status,
    get_inventory_summary,
    get_low_stock_products,
)
from app.tools.recommendations import get_reorder_recommendations
from app.tools.sales import compare_sales_periods, get_product_sales, get_sales_summary, get_sales_trend, get_top_products
from app.tools.suppliers import get_supplier_information, get_suppliers_summary


def test_full_range_sales_summary_calculations() -> None:
    summary = get_sales_summary()
    assert summary == {
        "start_date": "2025-01-01", "end_date": "2025-12-31",
        "total_revenue": 727516.76, "total_orders": 2000, "total_units": 6093,
        "average_order_value": 363.76, "unique_customers": 397,
    }
    assert summary["average_order_value"] == round(summary["total_revenue"] / summary["total_orders"], 2)


def test_filtered_sales_summary_is_inclusive() -> None:
    summary = get_sales_summary("2025-01-01", "2025-01-31")
    assert summary["total_revenue"] == 53413.82
    assert summary["total_orders"] == 142
    assert summary["total_units"] == 454
    assert summary["average_order_value"] == 376.15


def test_top_products_are_ranked_by_revenue_and_enriched() -> None:
    products = get_top_products(limit=2)
    assert [p["product_id"] for p in products] == ["PRD-028", "PRD-024"]
    assert products[0]["product_name"] == "Desk Lamp Plus"
    assert products[0]["revenue"] > products[1]["revenue"]
    assert products[0]["order_count"] == 128


@pytest.mark.parametrize("limit", [0, -1, True])
def test_top_products_rejects_invalid_limit(limit) -> None:
    with pytest.raises(ValueError):
        get_top_products(limit=limit)


def test_invalid_sales_period_is_rejected() -> None:
    with pytest.raises(ValueError, match="start_date"):
        get_sales_summary("2025-03-01", "2025-02-01")


def test_period_comparison_calculation_and_zero_safe_change() -> None:
    result = compare_sales_periods("2025-02-01", "2025-02-28", "2025-01-01", "2025-01-31")
    expected = round((result["period_a"]["total_revenue"] - 53413.82) / 53413.82 * 100, 2)
    assert result["percentage_changes"]["revenue"] == expected
    empty = compare_sales_periods("2026-01-01", "2026-01-31", "2027-01-01", "2027-01-31")
    assert empty["percentage_changes"] == {
        "revenue": None, "orders": None, "units": None, "average_order_value": None
    }


def test_product_sales_and_unknown_product() -> None:
    product = get_product_sales("PRD-028")
    assert product["revenue"] == 153212.4
    assert product["units_sold"] == 360
    assert product["average_unit_price"] == 425.59
    with pytest.raises(KeyError):
        get_product_sales("PRD-999")


def test_monthly_sales_trend_reconciles_with_full_summary() -> None:
    trend = get_sales_trend()
    summary = get_sales_summary()
    assert trend["start_date"] == "2025-01-01"
    assert trend["end_date"] == "2025-12-31"
    assert trend["granularity"] == "monthly"
    assert len(trend["points"]) == 12
    assert round(sum(point["revenue"] for point in trend["points"]), 2) == summary["total_revenue"]
    assert sum(point["orders"] for point in trend["points"]) == summary["total_orders"]
    assert sum(point["units"] for point in trend["points"]) == summary["total_units"]


def test_daily_filtered_sales_trend_reconciles_with_summary() -> None:
    trend = get_sales_trend("2025-01-01", "2025-01-31", "daily")
    summary = get_sales_summary("2025-01-01", "2025-01-31")
    assert trend["granularity"] == "daily"
    assert all(point["period"].startswith("2025-01-") for point in trend["points"])
    assert round(sum(point["revenue"] for point in trend["points"]), 2) == summary["total_revenue"]
    assert sum(point["orders"] for point in trend["points"]) == summary["total_orders"]


def test_sales_trend_rejects_invalid_arguments() -> None:
    with pytest.raises(ValueError, match="granularity"):
        get_sales_trend(granularity="weekly")
    with pytest.raises(ValueError, match="start_date"):
        get_sales_trend("2025-03-01", "2025-02-01")


@pytest.mark.parametrize(
    ("stock", "level", "expected"),
    [(50, 100, "Critical"), (51, 100, "Low Stock"), (100, 100, "Low Stock"), (101, 100, "Healthy")],
)
def test_inventory_status_thresholds(stock: int, level: int, expected: str) -> None:
    assert classify_inventory_status(stock, level) == expected


def test_low_stock_ordering_is_deterministic_and_urgent_first() -> None:
    products = get_low_stock_products()
    assert products[0]["product_id"] == "PRD-003"
    assert all(p["inventory_status"] != "Healthy" for p in products)
    keys = [
        (0 if p["inventory_status"] == "Critical" else 1, p["stock_ratio"], -p["lead_time_days"], p["product_id"])
        for p in products
    ]
    assert keys == sorted(keys)


def test_inventory_summary_matches_product_statuses() -> None:
    summary = get_inventory_summary()
    assert summary == {
        "total_products": 40, "healthy_products": 24, "low_stock_products": 10,
        "critical_products": 6, "total_units_in_stock": 2881, "percentage_at_risk": 40.0,
    }
    assert sum(summary[key] for key in ["healthy_products", "low_stock_products", "critical_products"]) == 40


def test_supplier_product_counts_and_risk_counts() -> None:
    supplier = get_supplier_information("SUP-001")
    assert supplier["number_of_products_supplied"] == 4
    assert [p["product_id"] for p in supplier["products"]] == ["PRD-001", "PRD-011", "PRD-021", "PRD-031"]
    summary = next(item for item in get_suppliers_summary() if item["supplier_id"] == "SUP-001")
    statuses = [p for p in get_inventory_status() if p["supplier_id"] == "SUP-001"]
    assert summary["products_at_risk"] == sum(p["inventory_status"] != "Healthy" for p in statuses)
    with pytest.raises(KeyError):
        get_supplier_information("SUP-999")


def test_reorder_recommendations_are_deterministic_and_use_dataset_date() -> None:
    first = get_reorder_recommendations()
    second = get_reorder_recommendations()
    assert first == second
    assert first["reference_date"] == "2025-12-31"
    assert first["recent_period_start"] == "2025-12-02"
    scores = [item["priority_score"] for item in first["recommendations"]]
    assert scores == sorted(scores, reverse=True)


def test_reorder_score_and_reason_match_exposed_evidence() -> None:
    item = get_reorder_recommendations(limit=1)["recommendations"][0]
    assert math.isclose(item["priority_score"], round(sum(item["score_components"].values()), 2))
    assert item["inventory_status"] in item["recommendation_reason"]
    assert str(item["recent_units_sold"]) in item["recommendation_reason"]
    assert str(item["lead_time_days"]) in item["recommendation_reason"]
