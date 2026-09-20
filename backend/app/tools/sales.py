"""Deterministic sales analytics tools."""

from datetime import date

import pandas as pd

from app.services.data_service import get_inventory_data, get_sales_data


def _parse_date(value: str | date | pd.Timestamp | None, name: str) -> pd.Timestamp | None:
    if value is None:
        return None
    try:
        parsed = pd.Timestamp(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a valid date") from exc
    if pd.isna(parsed):
        raise ValueError(f"{name} must be a valid date")
    return parsed.normalize()


def _filtered_sales(
    start_date: str | date | pd.Timestamp | None = None,
    end_date: str | date | pd.Timestamp | None = None,
) -> tuple[pd.DataFrame, pd.Timestamp, pd.Timestamp]:
    sales = get_sales_data()
    dataset_start = sales["date"].min().normalize()
    dataset_end = sales["date"].max().normalize()
    start = _parse_date(start_date, "start_date") or dataset_start
    end = _parse_date(end_date, "end_date") or dataset_end
    if start > end:
        raise ValueError("start_date must be on or before end_date")
    return sales.loc[sales["date"].between(start, end)].copy(), start, end


def _summary_for_frame(frame: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> dict[str, object]:
    total_revenue = round(float(frame["revenue"].sum()), 2)
    total_orders = int(frame["order_id"].nunique())
    return {
        "start_date": start.date().isoformat(),
        "end_date": end.date().isoformat(),
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "total_units": int(frame["quantity"].sum()),
        "average_order_value": round(total_revenue / total_orders, 2) if total_orders else 0.0,
        "unique_customers": int(frame["customer_id"].nunique()),
    }


def get_sales_summary(start_date=None, end_date=None) -> dict[str, object]:
    """Return sales KPIs for an inclusive period, or the full dataset when omitted."""
    frame, start, end = _filtered_sales(start_date, end_date)
    return _summary_for_frame(frame, start, end)


def get_top_products(start_date=None, end_date=None, limit: int = 5) -> list[dict[str, object]]:
    """Rank products by revenue for an inclusive period."""
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be a positive integer")
    sales, _, _ = _filtered_sales(start_date, end_date)
    grouped = sales.groupby("product_id", as_index=False).agg(
        units_sold=("quantity", "sum"), revenue=("revenue", "sum"), order_count=("order_id", "nunique")
    )
    inventory = get_inventory_data()[["product_id", "product_name", "category"]]
    ranked = grouped.merge(inventory, on="product_id", how="left").sort_values(
        ["revenue", "product_id"], ascending=[False, True]
    ).head(limit)
    return [
        {
            "product_id": str(row.product_id),
            "product_name": str(row.product_name),
            "category": str(row.category),
            "units_sold": int(row.units_sold),
            "revenue": round(float(row.revenue), 2),
            "order_count": int(row.order_count),
        }
        for row in ranked.itertuples(index=False)
    ]


def get_sales_trend(start_date=None, end_date=None, granularity: str = "monthly") -> dict[str, object]:
    """Return deterministic daily or monthly revenue, unique orders, and units."""
    if granularity not in {"daily", "monthly"}:
        raise ValueError("granularity must be 'daily' or 'monthly'")
    sales, start, end = _filtered_sales(start_date, end_date)
    if sales.empty:
        points: list[dict[str, object]] = []
    else:
        period_format = "%Y-%m-%d" if granularity == "daily" else "%Y-%m"
        grouped = (
            sales.assign(period=sales["date"].dt.strftime(period_format))
            .groupby("period", as_index=False)
            .agg(revenue=("revenue", "sum"), orders=("order_id", "nunique"), units=("quantity", "sum"))
            .sort_values("period")
        )
        points = [
            {
                "period": str(row.period),
                "revenue": round(float(row.revenue), 2),
                "orders": int(row.orders),
                "units": int(row.units),
            }
            for row in grouped.itertuples(index=False)
        ]
    return {
        "start_date": start.date().isoformat(),
        "end_date": end.date().isoformat(),
        "granularity": granularity,
        "points": points,
    }


def _percentage_change(current: float, baseline: float) -> float | None:
    return None if baseline == 0 else round((current - baseline) / baseline * 100, 2)


def compare_sales_periods(period_a_start, period_a_end, period_b_start, period_b_end) -> dict[str, object]:
    """Compare two inclusive periods; percentage change is A relative to B."""
    period_a = get_sales_summary(period_a_start, period_a_end)
    period_b = get_sales_summary(period_b_start, period_b_end)
    mapping = {
        "revenue": "total_revenue",
        "orders": "total_orders",
        "units": "total_units",
        "average_order_value": "average_order_value",
    }
    changes = {
        label: _percentage_change(float(period_a[field]), float(period_b[field]))
        for label, field in mapping.items()
    }
    return {"period_a": period_a, "period_b": period_b, "percentage_changes": changes}


def get_product_sales(product_id: str, start_date=None, end_date=None) -> dict[str, object]:
    """Return product metadata and sales KPIs; raise KeyError for an unknown product."""
    inventory = get_inventory_data()
    match = inventory.loc[inventory["product_id"] == product_id]
    if match.empty:
        raise KeyError(f"Unknown product_id: {product_id}")
    sales, start, end = _filtered_sales(start_date, end_date)
    product_sales = sales.loc[sales["product_id"] == product_id]
    product = match.iloc[0]
    units = int(product_sales["quantity"].sum())
    return {
        "product_id": product_id,
        "product_name": str(product["product_name"]),
        "category": str(product["category"]),
        "start_date": start.date().isoformat(),
        "end_date": end.date().isoformat(),
        "revenue": round(float(product_sales["revenue"].sum()), 2),
        "units_sold": units,
        "order_count": int(product_sales["order_id"].nunique()),
        "unique_customers": int(product_sales["customer_id"].nunique()),
        "average_unit_price": round(float(product_sales["revenue"].sum()) / units, 2) if units else 0.0,
    }
