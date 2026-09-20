"""Generate deterministic, synthetic business datasets for local development."""

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20250918
ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"

CATEGORIES = {
    "Office Supplies": ["Notebook", "Pen Set", "Desk Organizer", "Paper Ream", "File Folder"],
    "Technology": ["Keyboard", "Mouse", "Webcam", "USB Hub", "Headset"],
    "Furniture": ["Task Chair", "Standing Desk", "Desk Lamp", "Monitor Stand", "Bookshelf"],
    "Operations": ["Label Roll", "Packing Tape", "Storage Bin", "Safety Gloves", "Shipping Box"],
}
PRICE_RANGES = {
    "Office Supplies": (4.5, 38.0),
    "Technology": (22.0, 165.0),
    "Furniture": (35.0, 480.0),
    "Operations": (6.0, 72.0),
}


def generate_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(SEED)

    supplier_ids = [f"SUP-{i:03d}" for i in range(1, 11)]
    suppliers = pd.DataFrame(
        {
            "supplier_id": supplier_ids,
            "supplier_name": [f"Supplier {name}" for name in [
                "Atlas", "Beacon", "Cedar", "Delta", "Evergreen",
                "Foundry", "Granite", "Harbor", "Juniper", "Keystone",
            ]],
            "lead_time_days": [3, 5, 7, 9, 12, 15, 6, 10, 4, 14],
            "reliability_score": [0.97, 0.93, 0.88, 0.91, 0.84, 0.79, 0.95, 0.86, 0.98, 0.82],
        }
    )

    products: list[dict[str, object]] = []
    prices: dict[str, float] = {}
    product_number = 1
    stock_states = ["healthy"] * 24 + ["low"] * 10 + ["critical"] * 6
    rng.shuffle(stock_states)
    for category, base_names in CATEGORIES.items():
        low_price, high_price = PRICE_RANGES[category]
        for variant in range(2):
            for base_name in base_names:
                product_id = f"PRD-{product_number:03d}"
                reorder_level = int(rng.integers(20, 81))
                state = stock_states[product_number - 1]
                if state == "healthy":
                    current_stock = int(rng.integers(reorder_level + 15, reorder_level * 3 + 1))
                elif state == "low":
                    current_stock = int(rng.integers(max(1, reorder_level // 2), reorder_level + 1))
                else:
                    current_stock = int(rng.integers(0, max(2, reorder_level // 3)))
                prices[product_id] = round(float(rng.uniform(low_price, high_price)), 2)
                products.append(
                    {
                        "product_id": product_id,
                        "product_name": f"{base_name} {['Standard', 'Plus'][variant]}",
                        "category": category,
                        "current_stock": current_stock,
                        "reorder_level": reorder_level,
                        "supplier_id": supplier_ids[(product_number - 1) % len(supplier_ids)],
                    }
                )
                product_number += 1
    inventory = pd.DataFrame(products)

    product_ids = inventory["product_id"].tolist()
    popularity = rng.lognormal(mean=0.0, sigma=0.7, size=len(product_ids))
    popularity /= popularity.sum()
    dates = pd.date_range("2025-01-01", "2025-12-31", freq="D")
    seasonal_weights = np.array([0.8, 0.82, 0.9, 0.95, 1.0, 1.05, 0.98, 0.92, 1.02, 1.12, 1.35, 1.5])
    date_weights = np.array([seasonal_weights[d.month - 1] for d in dates], dtype=float)
    date_weights /= date_weights.sum()

    rows: list[dict[str, object]] = []
    for order_number in range(1, 2001):
        date = rng.choice(dates, p=date_weights)
        product_id = str(rng.choice(product_ids, p=popularity))
        quantity = int(rng.choice([1, 2, 3, 4, 5, 6, 8, 10], p=[0.3, 0.24, 0.17, 0.1, 0.07, 0.05, 0.04, 0.03]))
        unit_price = prices[product_id]
        rows.append(
            {
                "order_id": f"ORD-{order_number:05d}",
                "date": pd.Timestamp(date).strftime("%Y-%m-%d"),
                "customer_id": f"CUS-{int(rng.integers(1, 401)):04d}",
                "product_id": product_id,
                "quantity": quantity,
                "unit_price": unit_price,
                "revenue": round(quantity * unit_price, 2),
            }
        )
    sales = pd.DataFrame(rows).sort_values(["date", "order_id"]).reset_index(drop=True)
    return sales, inventory, suppliers


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    sales, inventory, suppliers = generate_data()
    sales.to_csv(DATA_DIR / "sales.csv", index=False)
    inventory.to_csv(DATA_DIR / "inventory.csv", index=False)
    suppliers.to_csv(DATA_DIR / "suppliers.csv", index=False)
    print(f"Generated {len(sales)} sales, {len(inventory)} products, and {len(suppliers)} suppliers.")


if __name__ == "__main__":
    main()

