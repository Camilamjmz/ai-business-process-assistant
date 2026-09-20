"""Validate relationships, types, calculations, and required values in sample data."""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"

REQUIRED_COLUMNS = {
    "sales": {"order_id", "date", "customer_id", "product_id", "quantity", "unit_price", "revenue"},
    "inventory": {"product_id", "product_name", "category", "current_stock", "reorder_level", "supplier_id"},
    "suppliers": {"supplier_id", "supplier_name", "lead_time_days", "reliability_score"},
}


def load_data(data_dir: Path = DATA_DIR) -> dict[str, pd.DataFrame]:
    return {name: pd.read_csv(data_dir / f"{name}.csv") for name in REQUIRED_COLUMNS}


def validate_data(data_dir: Path = DATA_DIR) -> list[str]:
    errors: list[str] = []
    try:
        frames = load_data(data_dir)
    except (FileNotFoundError, pd.errors.ParserError) as exc:
        return [f"Unable to load datasets: {exc}"]

    for name, required in REQUIRED_COLUMNS.items():
        missing = required - set(frames[name].columns)
        if missing:
            errors.append(f"{name}.csv is missing columns: {sorted(missing)}")

    if errors:
        return errors

    sales, inventory, suppliers = frames["sales"], frames["inventory"], frames["suppliers"]
    for name, frame, id_columns in [
        ("sales", sales, ["order_id", "customer_id", "product_id"]),
        ("inventory", inventory, ["product_id", "supplier_id"]),
        ("suppliers", suppliers, ["supplier_id"]),
    ]:
        if frame[id_columns].isna().any().any():
            errors.append(f"{name}.csv contains missing IDs")

    broken_products = set(sales["product_id"]) - set(inventory["product_id"])
    broken_suppliers = set(inventory["supplier_id"]) - set(suppliers["supplier_id"])
    if broken_products:
        errors.append(f"Unknown product references: {sorted(broken_products)}")
    if broken_suppliers:
        errors.append(f"Unknown supplier references: {sorted(broken_suppliers)}")

    numeric_rules = {
        "sales": {"quantity": 1, "unit_price": 0, "revenue": 0},
        "inventory": {"current_stock": 0, "reorder_level": 0},
        "suppliers": {"lead_time_days": 1, "reliability_score": 0},
    }
    for name, rules in numeric_rules.items():
        for column, minimum in rules.items():
            values = pd.to_numeric(frames[name][column], errors="coerce")
            if values.isna().any() or (values < minimum).any():
                errors.append(f"{name}.{column} contains invalid numeric values")

    expected_revenue = (sales["quantity"] * sales["unit_price"]).round(2)
    if not expected_revenue.equals(sales["revenue"].round(2)):
        errors.append("sales.revenue does not equal quantity * unit_price")
    if pd.to_datetime(sales["date"], errors="coerce").isna().any():
        errors.append("sales.date contains invalid dates")
    if not suppliers["reliability_score"].between(0, 1).all():
        errors.append("supplier reliability scores must be between 0 and 1")
    return errors


def main() -> None:
    errors = validate_data()
    if errors:
        raise SystemExit("Validation failed:\n- " + "\n- ".join(errors))
    print("All synthetic datasets are valid.")


if __name__ == "__main__":
    main()

