"""Transparent multi-source reorder recommendations."""

from datetime import timedelta

from app.services.data_service import get_sales_data
from app.tools.inventory import get_low_stock_products


def get_reorder_recommendations(limit: int | None = None) -> dict[str, object]:
    """Rank at-risk products using inventory, trailing-30-day demand, and supplier risk.

    Score = status (50 critical/25 low) + shortage severity (0–20) + normalized
    recent demand (0–15) + normalized lead time (0–10) + reliability risk (0–5).
    """
    if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 1):
        raise ValueError("limit must be a positive integer")
    sales = get_sales_data()
    reference_date = sales["date"].max().normalize()
    window_start = reference_date - timedelta(days=29)
    recent = sales.loc[sales["date"].between(window_start, reference_date)]
    demand = recent.groupby("product_id", as_index=False).agg(
        recent_units_sold=("quantity", "sum"), recent_revenue=("revenue", "sum")
    ).set_index("product_id")
    candidates = get_low_stock_products()
    max_units = max([int(demand.loc[p["product_id"], "recent_units_sold"]) if p["product_id"] in demand.index else 0 for p in candidates], default=0)
    max_lead = max([int(p["lead_time_days"]) for p in candidates], default=1)
    recommendations = []
    for product in candidates:
        product_id = str(product["product_id"])
        units = int(demand.loc[product_id, "recent_units_sold"]) if product_id in demand.index else 0
        revenue = float(demand.loc[product_id, "recent_revenue"]) if product_id in demand.index else 0.0
        status_points = 50.0 if product["inventory_status"] == "Critical" else 25.0
        shortage_points = round((1 - min(float(product["stock_ratio"]), 1)) * 20, 2)
        demand_points = round(units / max_units * 15, 2) if max_units else 0.0
        lead_time_points = round(int(product["lead_time_days"]) / max_lead * 10, 2) if max_lead else 0.0
        reliability_points = round((1 - float(product["reliability_score"])) * 5, 2)
        score = round(status_points + shortage_points + demand_points + lead_time_points + reliability_points, 2)
        item = dict(product)
        item.update({
            "recent_units_sold": units, "recent_revenue": round(revenue, 2),
            "score_components": {
                "status_points": status_points, "shortage_points": shortage_points,
                "demand_points": demand_points, "lead_time_points": lead_time_points,
                "reliability_points": reliability_points,
            },
            "priority_score": score,
            "recommendation_reason": (
                f"{product['inventory_status']} stock at {float(product['stock_ratio']) * 100:.1f}% of reorder level; "
                f"{units} units sold in the trailing 30 days; supplier lead time is {product['lead_time_days']} days."
            ),
        })
        recommendations.append(item)
    recommendations.sort(key=lambda p: (-float(p["priority_score"]), str(p["product_id"])))
    return {
        "reference_date": reference_date.date().isoformat(),
        "recent_period_start": window_start.date().isoformat(),
        "recent_period_end": reference_date.date().isoformat(),
        "recommendations": recommendations[:limit] if limit is not None else recommendations,
    }

