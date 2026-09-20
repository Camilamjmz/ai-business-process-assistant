from pathlib import Path

import pandas as pd

from scripts.validate_data import load_data, validate_data

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def test_datasets_pass_full_validation() -> None:
    assert validate_data(DATA_DIR) == []


def test_revenue_is_quantity_times_unit_price() -> None:
    sales = pd.read_csv(DATA_DIR / "sales.csv")
    expected = (sales["quantity"] * sales["unit_price"]).round(2)
    pd.testing.assert_series_equal(sales["revenue"].round(2), expected, check_names=False)


def test_product_and_supplier_references_are_valid() -> None:
    frames = load_data(DATA_DIR)
    assert set(frames["sales"]["product_id"]) <= set(frames["inventory"]["product_id"])
    assert set(frames["inventory"]["supplier_id"]) <= set(frames["suppliers"]["supplier_id"])

