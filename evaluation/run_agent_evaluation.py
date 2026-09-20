"""Validate or run the transparent agent benchmark without exposing credentials."""

import argparse
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.agents.business_agent import AgentUpstreamError, run_business_agent  # noqa: E402
from app.agents.tool_registry import TOOL_REGISTRY  # noqa: E402
from app.tools.inventory import get_inventory_summary, get_low_stock_products  # noqa: E402
from app.tools.recommendations import get_reorder_recommendations  # noqa: E402
from app.tools.sales import get_product_sales, get_sales_summary, get_top_products  # noqa: E402
from app.tools.suppliers import get_supplier_information  # noqa: E402

CASES_PATH = ROOT / "evaluation" / "agent_cases.json"
RESULTS_PATH = ROOT / "evaluation" / "results" / "agent_evaluation_latest.json"
FRONTEND_RESULTS_PATH = ROOT / "frontend" / "public" / "evaluation" / "agent_evaluation_latest.json"
REQUIRED_FIELDS = {"id", "category", "prompt", "expected_tools", "requires_tool"}


def load_cases(path: Path = CASES_PATH) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Evaluation dataset must be a JSON list")
    return data


def deterministic_fact_snapshot() -> dict[str, set[str]]:
    summary = get_sales_summary()
    product = get_product_sales("PRD-028")
    inventory = get_inventory_summary()
    supplier = get_supplier_information("SUP-001")
    reorder = get_reorder_recommendations(3)["recommendations"]
    return {
        "EVAL-001": {f"{summary['total_revenue']:,.2f}"},
        "EVAL-002": {f"{summary['total_orders']:,}", f"{summary['total_units']:,}"},
        "EVAL-003": {f"{summary['average_order_value']:,.2f}", str(summary["unique_customers"])},
        "EVAL-004": {get_top_products(limit=1)[0]["product_id"]},
        "EVAL-007": {f"{product['revenue']:,.2f}", str(product["units_sold"])},
        "EVAL-008": {str(inventory[key]) for key in ["total_products", "healthy_products", "low_stock_products", "critical_products"]},
        "EVAL-009": {get_low_stock_products()[0]["product_id"]},
        "EVAL-011": {str(supplier["supplier_name"]), str(supplier["products"][0]["product_id"])},
        "EVAL-013": {str(item["product_id"]) for item in reorder},
        "EVAL-014": {str(reorder[0]["product_id"])},
    }


def validate_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    ids: list[str] = []
    known_tools = set(TOOL_REGISTRY)
    for index, case in enumerate(cases):
        missing = REQUIRED_FIELDS - set(case)
        if missing:
            errors.append(f"Case {index} missing fields: {sorted(missing)}")
            continue
        case_id = case["id"]
        ids.append(case_id)
        if not isinstance(case_id, str) or not case_id.startswith("EVAL-"):
            errors.append(f"Case {index} has invalid id")
        if not isinstance(case["prompt"], str) or not case["prompt"].strip():
            errors.append(f"{case_id} has an empty prompt")
        if not isinstance(case["requires_tool"], bool):
            errors.append(f"{case_id} requires_tool must be boolean")
        expected = case["expected_tools"]
        if not isinstance(expected, list) or any(not isinstance(tool, str) for tool in expected):
            errors.append(f"{case_id} expected_tools must be a string list")
        else:
            unknown = set(expected) - known_tools
            if unknown:
                errors.append(f"{case_id} contains unknown tools: {sorted(unknown)}")
            if case["requires_tool"] and not expected:
                errors.append(f"{case_id} requires a tool but declares none")
    duplicates = sorted(item for item, count in Counter(ids).items() if count > 1)
    if duplicates:
        errors.append(f"Duplicate case IDs: {duplicates}")
    snapshots = deterministic_fact_snapshot()
    for case in cases:
        expected_facts = set(case.get("expected_facts", []))
        if case.get("id") in snapshots and expected_facts != snapshots[case["id"]]:
            errors.append(f"{case['id']} expected facts do not match deterministic analytics")
    return {"valid": not errors, "case_count": len(cases), "categories": dict(sorted(Counter(case.get("category", "unknown") for case in cases).items())), "registered_tool_count": len(known_tools), "errors": errors}


def is_service_unavailable(error: Exception) -> bool:
    current: BaseException | None = error
    while current:
        text = str(current).upper()
        if "503" in text or "UNAVAILABLE" in text or "HIGH DEMAND" in text:
            return True
        current = current.__cause__ or current.__context__
    return False


def is_quota_exhausted(error: Exception) -> bool:
    current: BaseException | None = error
    while current:
        text = str(current).upper()
        if "429" in text or "RESOURCE_EXHAUSTED" in text or "QUOTA EXCEEDED" in text:
            return True
        current = current.__cause__ or current.__context__
    return False


def run_live(cases: list[dict[str, Any]], retries: int = 2, delay_seconds: float = 2.0) -> dict[str, Any]:
    results = []
    for case in cases:
        outcome: dict[str, Any] | None = None
        for attempt in range(retries + 1):
            try:
                response = run_business_agent(case["prompt"])
                used = response["tools_used"]
                expected = case["expected_tools"]
                facts = case.get("expected_facts", [])
                outcome = {
                    "id": case["id"], "category": case["category"], "status": "completed",
                    "tools_used": used, "expected_tools": expected,
                    "tool_selection_correct": set(used) == set(expected),
                    "required_tool_used": (not case["requires_tool"]) or bool(used),
                    "unexpected_tool": bool(set(used) - set(expected)),
                    "numeric_facts_matched": all(str(fact).lower() in response["answer"].lower() for fact in facts),
                    "tool_call_count": len(response["tool_calls"]),
                    "execution_time_ms": response["total_execution_time_ms"],
                    "attempts": attempt + 1,
                }
                break
            except AgentUpstreamError as exc:
                unavailable = is_service_unavailable(exc)
                quota_exhausted = is_quota_exhausted(exc)
                if unavailable and attempt < retries:
                    time.sleep(delay_seconds)
                    continue
                status = "quota_exhausted" if quota_exhausted else "service_unavailable" if unavailable else "upstream_failure"
                outcome = {"id": case["id"], "category": case["category"], "status": status, "tools_used": [], "expected_tools": case["expected_tools"], "attempts": attempt + 1}
                break
            except Exception:
                outcome = {"id": case["id"], "category": case["category"], "status": "logical_failure", "tools_used": [], "expected_tools": case["expected_tools"], "attempts": attempt + 1}
                break
        results.append(outcome)
        time.sleep(0.5)

    completed = [item for item in results if item["status"] == "completed"]
    count = len(completed)
    metrics = {
        "evaluation_cases": len(cases),
        "completed_cases": count,
        "service_unavailable_cases": sum(item["status"] == "service_unavailable" for item in results),
        "quota_exhausted_cases": sum(item["status"] == "quota_exhausted" for item in results),
        "successful_completion_rate": round(count / len(cases) * 100, 2) if cases else 0.0,
        "tool_selection_accuracy": round(sum(item["tool_selection_correct"] for item in completed) / count * 100, 2) if count else None,
        "required_tool_usage_rate": round(sum(item["required_tool_used"] for item in completed) / count * 100, 2) if count else None,
        "unexpected_tool_rate": round(sum(item["unexpected_tool"] for item in completed) / count * 100, 2) if count else None,
        "numeric_fact_match_rate": round(sum(item["numeric_facts_matched"] for item in completed) / count * 100, 2) if count else None,
        "average_tool_calls": round(sum(item["tool_call_count"] for item in completed) / count, 2) if count else None,
        "average_execution_time_ms": round(sum(item["execution_time_ms"] for item in completed) / count, 2) if count else None,
    }
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "mode": "live", "model": os.getenv("GEMINI_MODEL", "gemini-3.6-flash"), "metrics": metrics, "category_counts": dict(sorted(Counter(case["category"] for case in cases).items())), "cases": results}


def write_results(result: dict[str, Any]) -> None:
    for path in [RESULTS_PATH, FRONTEND_RESULTS_PATH]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["offline", "live"], default="offline")
    args = parser.parse_args()
    cases = load_cases()
    validation = validate_cases(cases)
    if not validation["valid"]:
        raise SystemExit("Evaluation validation failed:\n- " + "\n- ".join(validation["errors"]))
    if args.mode == "offline":
        print(json.dumps(validation, indent=2))
        return
    load_dotenv(ROOT / ".env")
    if not os.getenv("GEMINI_API_KEY"):
        raise SystemExit("GEMINI_API_KEY is required for live mode")
    result = run_live(cases)
    write_results(result)
    print(json.dumps(result["metrics"], indent=2))


if __name__ == "__main__":
    main()
