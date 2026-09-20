"""Deterministic inventory analytics tools."""

from app.services.data_service import get_inventory_data, get_suppliers_data


def classify_inventory_status(current_stock: int, reorder_level: int) -> str:
    """Classify stock as Critical (<=50%), Low Stock (<=100%), or Healthy (>100%)."""
    if reorder_level <= 0:
        raise ValueError("reorder_level must be positive")
    if current_stock <= reorder_level * 0.5:
        return "Critical"
    if current_stock <= reorder_level:
        return "Low Stock"
    return "Healthy"


def get_inventory_status() -> list[dict[str, object]]:
    """Return every product enriched with supplier data and deterministic status."""
    merged = get_inventory_data().merge(get_suppliers_data(), on="supplier_id", how="left")
    results = []
    for row in merged.itertuples(index=False):
        results.append({
            "product_id": str(row.product_id), "product_name": str(row.product_name),
            "category": str(row.category), "current_stock": int(row.current_stock),
            "reorder_level": int(row.reorder_level),
            "inventory_status": classify_inventory_status(int(row.current_stock), int(row.reorder_level)),
            "supplier_id": str(row.supplier_id), "supplier_name": str(row.supplier_name),
            "lead_time_days": int(row.lead_time_days), "reliability_score": float(row.reliability_score),
        })
    return results


def get_low_stock_products() -> list[dict[str, object]]:
    """Return at-risk products ordered by status, stock ratio, lead time, then ID."""
    products = []
    for product in get_inventory_status():
        if product["inventory_status"] == "Healthy":
            continue
        item = dict(product)
        item["stock_ratio"] = round(int(item["current_stock"]) / int(item["reorder_level"]), 4)
        item["units_below_reorder_level"] = max(0, int(item["reorder_level"]) - int(item["current_stock"]))
        products.append(item)
    rank = {"Critical": 0, "Low Stock": 1}
    return sorted(products, key=lambda p: (rank[str(p["inventory_status"])], p["stock_ratio"], -int(p["lead_time_days"]), p["product_id"]))


def get_inventory_summary() -> dict[str, int | float]:
    """Return product counts, units, and percentage of products at risk."""
    products = get_inventory_status()
    counts = {status: sum(p["inventory_status"] == status for p in products) for status in ["Healthy", "Low Stock", "Critical"]}
    at_risk = counts["Low Stock"] + counts["Critical"]
    return {
        "total_products": len(products), "healthy_products": counts["Healthy"],
        "low_stock_products": counts["Low Stock"], "critical_products": counts["Critical"],
        "total_units_in_stock": sum(int(p["current_stock"]) for p in products),
        "percentage_at_risk": round(at_risk / len(products) * 100, 2) if products else 0.0,
    }

