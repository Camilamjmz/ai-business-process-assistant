"""Validated, cached access to the project's synthetic CSV datasets."""

from functools import lru_cache
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"

EXPECTED_COLUMNS = {
    "sales": {"order_id", "date", "customer_id", "product_id", "quantity", "unit_price", "revenue"},
    "inventory": {"product_id", "product_name", "category", "current_stock", "reorder_level", "supplier_id"},
    "suppliers": {"supplier_id", "supplier_name", "lead_time_days", "reliability_score"},
}


def _load_csv(name: str) -> pd.DataFrame:
    frame = pd.read_csv(DATA_DIR / f"{name}.csv", parse_dates=["date"] if name == "sales" else None)
    missing = EXPECTED_COLUMNS[name] - set(frame.columns)
    if missing:
        raise ValueError(f"{name}.csv is missing required columns: {sorted(missing)}")
    return frame


@lru_cache(maxsize=1)
def _cached_datasets() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return _load_csv("sales"), _load_csv("inventory"), _load_csv("suppliers")


def get_sales_data() -> pd.DataFrame:
    """Return a defensive copy of sales data with parsed dates."""
    return _cached_datasets()[0].copy()


def get_inventory_data() -> pd.DataFrame:
    """Return a defensive copy of inventory data."""
    return _cached_datasets()[1].copy()


def get_suppliers_data() -> pd.DataFrame:
    """Return a defensive copy of supplier data."""
    return _cached_datasets()[2].copy()


def clear_data_cache() -> None:
    """Clear cached datasets, primarily for tests and controlled refreshes."""
    _cached_datasets.cache_clear()

