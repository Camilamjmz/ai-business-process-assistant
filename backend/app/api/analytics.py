"""HTTP routes for deterministic analytics tools."""

from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.tools.inventory import get_inventory_status, get_inventory_summary, get_low_stock_products
from app.tools.recommendations import get_reorder_recommendations
from app.tools.sales import compare_sales_periods, get_product_sales, get_sales_summary, get_sales_trend, get_top_products
from app.tools.suppliers import get_supplier_information, get_suppliers_summary

router = APIRouter(prefix="/api")


def _bad_request(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


@router.get("/sales/summary", tags=["sales"])
def sales_summary(start_date: date | None = None, end_date: date | None = None):
    try:
        return get_sales_summary(start_date, end_date)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/sales/top-products", tags=["sales"])
def top_products(start_date: date | None = None, end_date: date | None = None, limit: int = Query(5, ge=1)):
    try:
        return get_top_products(start_date, end_date, limit)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/sales/trend", tags=["sales"])
def sales_trend(
    start_date: date | None = None,
    end_date: date | None = None,
    granularity: str = Query("monthly", pattern="^(daily|monthly)$"),
):
    try:
        return get_sales_trend(start_date, end_date, granularity)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/sales/compare", tags=["sales"])
def compare_sales(period_a_start: date, period_a_end: date, period_b_start: date, period_b_end: date):
    try:
        return compare_sales_periods(period_a_start, period_a_end, period_b_start, period_b_end)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/products/{product_id}/sales", tags=["sales"])
def product_sales(product_id: str, start_date: date | None = None, end_date: date | None = None):
    try:
        return get_product_sales(product_id, start_date, end_date)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/inventory", tags=["inventory"])
def inventory_status():
    return get_inventory_status()


@router.get("/inventory/summary", tags=["inventory"])
def inventory_summary():
    return get_inventory_summary()


@router.get("/inventory/low-stock", tags=["inventory"])
def low_stock_products():
    return get_low_stock_products()


@router.get("/inventory/reorder-recommendations", tags=["inventory"])
def reorder_recommendations(limit: int | None = Query(None, ge=1)):
    return get_reorder_recommendations(limit)


@router.get("/suppliers", tags=["suppliers"])
def suppliers_summary():
    return get_suppliers_summary()


@router.get("/suppliers/{supplier_id}", tags=["suppliers"])
def supplier_information(supplier_id: str):
    try:
        return get_supplier_information(supplier_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc
