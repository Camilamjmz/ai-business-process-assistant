"""Deterministic supplier analytics tools."""

from app.services.data_service import get_inventory_data, get_suppliers_data
from app.tools.inventory import get_inventory_status


def get_supplier_information(supplier_id: str) -> dict[str, object]:
    """Return a supplier and its products; raise KeyError when unknown."""
    suppliers = get_suppliers_data()
    match = suppliers.loc[suppliers["supplier_id"] == supplier_id]
    if match.empty:
        raise KeyError(f"Unknown supplier_id: {supplier_id}")
    supplier = match.iloc[0]
    products = get_inventory_data().loc[lambda frame: frame["supplier_id"] == supplier_id].sort_values("product_id")
    product_list = [
        {"product_id": str(row.product_id), "product_name": str(row.product_name)}
        for row in products.itertuples(index=False)
    ]
    return {
        "supplier_id": supplier_id,
        "supplier_name": str(supplier["supplier_name"]),
        "lead_time_days": int(supplier["lead_time_days"]),
        "reliability_score": float(supplier["reliability_score"]),
        "number_of_products_supplied": len(product_list),
        "products": product_list,
    }


def get_suppliers_summary() -> list[dict[str, object]]:
    """Return all suppliers with supplied-product and at-risk-product counts."""
    inventory = get_inventory_status()
    results = []
    for row in get_suppliers_data().sort_values("supplier_id").itertuples(index=False):
        products = [p for p in inventory if p["supplier_id"] == row.supplier_id]
        results.append({
            "supplier_id": str(row.supplier_id), "supplier_name": str(row.supplier_name),
            "lead_time_days": int(row.lead_time_days), "reliability_score": float(row.reliability_score),
            "products_supplied": len(products),
            "products_at_risk": sum(p["inventory_status"] != "Healthy" for p in products),
        })
    return results

