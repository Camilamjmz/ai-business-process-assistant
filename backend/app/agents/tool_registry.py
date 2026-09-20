"""Allow-listed adapters between Gemini function calls and analytics tools."""

from dataclasses import dataclass
from datetime import date
from typing import Any, Callable

from app.tools.inventory import get_inventory_status, get_inventory_summary, get_low_stock_products
from app.tools.recommendations import get_reorder_recommendations
from app.tools.sales import compare_sales_periods, get_product_sales, get_sales_summary, get_top_products
from app.tools.suppliers import get_supplier_information, get_suppliers_summary


class ToolRegistryError(ValueError):
    """A requested tool or its arguments are not allowed."""


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    function: Callable[..., Any]
    activity_label: str
    result_label: str


def _object_schema(properties: dict[str, dict[str, Any]] | None = None, required: list[str] | None = None):
    schema: dict[str, Any] = {"type": "object", "properties": properties or {}, "additionalProperties": False}
    if required:
        schema["required"] = required
    return schema


DATE = {"type": "string", "format": "date", "description": "ISO date in YYYY-MM-DD format."}
LIMIT = {"type": "integer", "minimum": 1, "description": "Positive maximum number of results."}

TOOL_REGISTRY: dict[str, ToolSpec] = {
    "get_sales_summary": ToolSpec("get_sales_summary", "Use for overall revenue, orders, units, average order value, or customer counts for a full or inclusive date range.", _object_schema({"start_date": DATE, "end_date": DATE}), get_sales_summary, "Reviewing sales performance", "Sales analysis complete"),
    "get_top_products": ToolSpec("get_top_products", "Use when asked which products lead or rank by sales revenue in a full or inclusive date range.", _object_schema({"start_date": DATE, "end_date": DATE, "limit": LIMIT}), get_top_products, "Ranking products by revenue", "Product ranking complete"),
    "compare_sales_periods": ToolSpec("compare_sales_periods", "Use to compare revenue, orders, units, and average order value between two explicit periods.", _object_schema({"period_a_start": DATE, "period_a_end": DATE, "period_b_start": DATE, "period_b_end": DATE}, ["period_a_start", "period_a_end", "period_b_start", "period_b_end"]), compare_sales_periods, "Comparing sales periods", "Period comparison complete"),
    "get_product_sales": ToolSpec("get_product_sales", "Use for sales metrics about one known product ID, optionally within an inclusive date range.", _object_schema({"product_id": {"type": "string", "description": "Product ID such as PRD-001."}, "start_date": DATE, "end_date": DATE}, ["product_id"]), get_product_sales, "Checking product sales", "Product sales analysis complete"),
    "get_inventory_status": ToolSpec("get_inventory_status", "Use when the user needs the stock status and supplier evidence for all products.", _object_schema(), get_inventory_status, "Reviewing inventory status", "Inventory review complete"),
    "get_low_stock_products": ToolSpec("get_low_stock_products", "Use to identify Critical and Low Stock products in deterministic urgency order.", _object_schema(), get_low_stock_products, "Checking inventory risk", "Inventory risk analysis complete"),
    "get_inventory_summary": ToolSpec("get_inventory_summary", "Use for aggregate inventory counts, units in stock, or percentage of products at risk.", _object_schema(), get_inventory_summary, "Summarizing inventory", "Inventory summary complete"),
    "get_supplier_information": ToolSpec("get_supplier_information", "Use for details and supplied products for one known supplier ID.", _object_schema({"supplier_id": {"type": "string", "description": "Supplier ID such as SUP-001."}}, ["supplier_id"]), get_supplier_information, "Checking supplier details", "Supplier analysis complete"),
    "get_suppliers_summary": ToolSpec("get_suppliers_summary", "Use to compare all suppliers, including product coverage and products currently at risk.", _object_schema(), get_suppliers_summary, "Reviewing suppliers", "Supplier review complete"),
    "get_reorder_recommendations": ToolSpec("get_reorder_recommendations", "Use when asked which products should be reordered, restocked, prioritized for purchasing, or require inventory action. It combines inventory risk, recent sales demand, supplier lead time, and supplier reliability using deterministic logic.", _object_schema({"limit": LIMIT}), get_reorder_recommendations, "Prioritizing reorder candidates", "Reorder analysis complete"),
}


def get_tool_declarations() -> list[dict[str, Any]]:
    """Return Gemini-compatible declarations for every allow-listed tool."""
    return [{"name": spec.name, "description": spec.description, "parameters_json_schema": spec.parameters} for spec in TOOL_REGISTRY.values()]


def _validate_value(name: str, value: Any, schema: dict[str, Any]) -> Any:
    expected = schema["type"]
    if expected == "integer":
        if isinstance(value, bool) or not isinstance(value, int) or value < schema.get("minimum", value):
            raise ToolRegistryError(f"{name} must be a positive integer")
    elif expected == "string":
        if not isinstance(value, str) or not value.strip():
            raise ToolRegistryError(f"{name} must be a non-empty string")
        value = value.strip()
        if schema.get("format") == "date":
            try:
                date.fromisoformat(value)
            except ValueError as exc:
                raise ToolRegistryError(f"{name} must use YYYY-MM-DD format") from exc
    return value


def invoke_tool(name: str, arguments: dict[str, Any] | None) -> Any:
    """Validate and invoke one allow-listed deterministic analytics tool."""
    spec = TOOL_REGISTRY.get(name)
    if spec is None:
        raise ToolRegistryError(f"Unknown tool requested: {name}")
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        raise ToolRegistryError("Tool arguments must be an object")
    properties = spec.parameters["properties"]
    unknown = set(arguments) - set(properties)
    if unknown:
        raise ToolRegistryError(f"Unexpected arguments for {name}: {sorted(unknown)}")
    missing = set(spec.parameters.get("required", [])) - set(arguments)
    if missing:
        raise ToolRegistryError(f"Missing required arguments for {name}: {sorted(missing)}")
    validated = {key: _validate_value(key, value, properties[key]) for key, value in arguments.items()}
    return spec.function(**validated)

