import copy

from app.agents.tool_registry import TOOL_REGISTRY
from evaluation.run_agent_evaluation import is_quota_exhausted, is_service_unavailable, load_cases, validate_cases


def test_evaluation_dataset_schema_and_deterministic_facts() -> None:
    result = validate_cases(load_cases())
    assert result["valid"] is True
    assert result["case_count"] == 20
    assert result["registered_tool_count"] == len(TOOL_REGISTRY)
    assert result["errors"] == []


def test_evaluation_ids_are_unique() -> None:
    cases = load_cases()
    assert len({case["id"] for case in cases}) == len(cases)


def test_duplicate_evaluation_ids_are_rejected() -> None:
    cases = copy.deepcopy(load_cases())
    cases[1]["id"] = cases[0]["id"]
    result = validate_cases(cases)
    assert result["valid"] is False
    assert any("Duplicate case IDs" in error for error in result["errors"])


def test_unknown_expected_tool_is_rejected() -> None:
    cases = copy.deepcopy(load_cases())
    cases[0]["expected_tools"] = ["delete_inventory"]
    result = validate_cases(cases)
    assert result["valid"] is False
    assert any("unknown tools" in error for error in result["errors"])


def test_missing_required_case_field_is_rejected() -> None:
    cases = copy.deepcopy(load_cases())
    del cases[0]["prompt"]
    result = validate_cases(cases)
    assert result["valid"] is False
    assert any("missing fields" in error for error in result["errors"])


def test_upstream_availability_categories_are_distinct() -> None:
    quota = RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded")
    unavailable = RuntimeError("503 UNAVAILABLE: model high demand")
    assert is_quota_exhausted(quota) is True
    assert is_service_unavailable(quota) is False
    assert is_service_unavailable(unavailable) is True
    assert is_quota_exhausted(unavailable) is False
