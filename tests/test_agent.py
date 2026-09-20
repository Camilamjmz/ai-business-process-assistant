from dataclasses import replace
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from google.genai import errors
from google.genai import types

from app.agents.business_agent import (
    MAX_MESSAGE_LENGTH,
    AgentConfigurationError,
    AgentLoopLimitError,
    AgentToolError,
    AgentUpstreamError,
    AgentValidationError,
    run_business_agent,
)
from app.agents.tool_registry import TOOL_REGISTRY, ToolRegistryError, invoke_tool
from app.main import app


def response_with_text(text: str):
    return SimpleNamespace(function_calls=[], text=text, candidates=[])


def response_with_calls(*calls: tuple[str, dict]):
    function_calls = [SimpleNamespace(name=name, args=args) for name, args in calls]
    content = types.Content(
        role="model",
        parts=[types.Part.from_function_call(name=name, args=args) for name, args in calls],
    )
    return SimpleNamespace(function_calls=function_calls, text=None, candidates=[SimpleNamespace(content=content)])


class FakeModels:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def generate_content(self, **kwargs):
        self.requests.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeClient:
    def __init__(self, responses):
        self.models = FakeModels(responses)


def test_missing_api_key_is_clear_and_does_not_prevent_import(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(AgentConfigurationError, match="not configured"):
        run_business_agent("What was total revenue?")
    response = TestClient(app).post("/api/assistant/query", json={"message": "What was total revenue?"})
    assert response.status_code == 503
    assert response.json() == {"detail": "AI assistant is not configured"}


@pytest.mark.parametrize("message", ["", "   ", "\n"])
def test_empty_message_is_rejected(message: str) -> None:
    with pytest.raises(AgentValidationError):
        run_business_agent(message, client=FakeClient([]))


def test_oversized_message_is_rejected() -> None:
    with pytest.raises(AgentValidationError, match="must not exceed"):
        run_business_agent("x" * (MAX_MESSAGE_LENGTH + 1), client=FakeClient([]))
    response = TestClient(app).post("/api/assistant/query", json={"message": "x" * (MAX_MESSAGE_LENGTH + 1)})
    assert response.status_code == 422


def test_non_data_question_can_return_without_tools() -> None:
    result = run_business_agent("What can you help me with?", client=FakeClient([response_with_text("I can analyze sales and inventory.")]))
    assert result["answer"] == "I can analyze sales and inventory."
    assert result["tools_used"] == []
    assert result["tool_calls"] == []


def test_model_can_be_configured_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test-model")
    client = FakeClient([response_with_text("Configured model response")])
    result = run_business_agent("What can you help me with?", client=client)
    assert result["model"] == "gemini-test-model"
    assert client.models.requests[0]["model"] == "gemini-test-model"


@pytest.mark.parametrize(
    ("question", "tool_name"),
    [
        ("What was total revenue?", "get_sales_summary"),
        ("How many products are at risk?", "get_inventory_summary"),
        ("Which products should we reorder?", "get_reorder_recommendations"),
    ],
)
def test_business_questions_execute_the_requested_grounding_tool(question: str, tool_name: str) -> None:
    client = FakeClient([response_with_calls((tool_name, {})), response_with_text("Grounded answer")])
    result = run_business_agent(question, client=client)
    assert result["tools_used"] == [tool_name]
    assert result["tool_calls"][0]["success"] is True
    assert len(client.models.requests) == 2
    assert client.models.requests[1]["contents"][-1].parts[0].function_response.name == tool_name


def test_tool_arguments_are_validated() -> None:
    with pytest.raises(ToolRegistryError, match="positive integer"):
        invoke_tool("get_top_products", {"limit": 0})
    with pytest.raises(ToolRegistryError, match="Unexpected"):
        invoke_tool("get_sales_summary", {"secret": "value"})
    with pytest.raises(ToolRegistryError, match="YYYY-MM-DD"):
        invoke_tool("get_sales_summary", {"start_date": "January"})


def test_unknown_tool_request_is_rejected() -> None:
    with pytest.raises(AgentToolError, match="unavailable"):
        run_business_agent("Do something", client=FakeClient([response_with_calls(("delete_inventory", {}))]))


def test_tool_exception_is_sanitized_and_returned_to_model(monkeypatch) -> None:
    def fail_tool():
        raise RuntimeError("database-password-should-not-leak")

    monkeypatch.setitem(TOOL_REGISTRY, "get_inventory_summary", replace(TOOL_REGISTRY["get_inventory_summary"], function=fail_tool))
    client = FakeClient([response_with_calls(("get_inventory_summary", {})), response_with_text("The analysis was unavailable.")])
    result = run_business_agent("Summarize inventory", client=client)
    assert result["tool_calls"][0]["success"] is False
    function_response = client.models.requests[1]["contents"][-1].parts[0].function_response.response
    assert function_response == {"error": "Tool execution failed"}
    assert "password" not in str(result)


def test_multiple_tool_calls_work_in_one_round() -> None:
    client = FakeClient([
        response_with_calls(("get_sales_summary", {}), ("get_inventory_summary", {})),
        response_with_text("Sales and inventory answer"),
    ])
    result = run_business_agent("Summarize sales and inventory", client=client)
    assert result["tools_used"] == ["get_sales_summary", "get_inventory_summary"]
    assert len(result["tool_calls"]) == 2
    assert len(client.models.requests[1]["contents"][-1].parts) == 2


def test_maximum_tool_loop_is_enforced() -> None:
    calls = [response_with_calls(("get_inventory_summary", {})) for _ in range(6)]
    with pytest.raises(AgentLoopLimitError, match="5 rounds"):
        run_business_agent("Keep checking", client=FakeClient(calls))


def test_tool_activity_trace_contains_sanitized_events() -> None:
    result = run_business_agent(
        "What was total revenue?",
        client=FakeClient([response_with_calls(("get_sales_summary", {})), response_with_text("Revenue answer")]),
    )
    assert [event["type"] for event in result["activity"]] == [
        "request_received", "tool_call", "tool_result", "response_generated"
    ]
    assert result["activity"][1]["tool_name"] == "get_sales_summary"


def test_upstream_errors_never_include_api_key(monkeypatch, caplog) -> None:
    secret = "super-secret-test-key"
    monkeypatch.setenv("GEMINI_API_KEY", secret)
    with pytest.raises(AgentUpstreamError) as captured:
        run_business_agent("Hello", client=FakeClient([RuntimeError(secret)]))
    assert secret not in str(captured.value)
    assert secret not in caplog.text


@pytest.mark.parametrize(
    ("code", "status", "category"),
    [
        (429, "RESOURCE_EXHAUSTED", "quota_exhausted"),
        (503, "UNAVAILABLE", "service_unavailable"),
        (404, "NOT_FOUND", "model_unavailable"),
        (403, "PERMISSION_DENIED", "authentication_or_permission"),
        (400, "INVALID_ARGUMENT", "invalid_request"),
    ],
)
def test_google_errors_are_logged_safely(caplog, code, status, category) -> None:
    upstream = errors.APIError(code, {"error": {"status": status, "message": "Safe diagnostic message"}})
    with pytest.raises(AgentUpstreamError, match="Gemini service request failed"):
        run_business_agent("Hello", client=FakeClient([upstream]), model="gemini-test-model")

    assert f"exception_class=APIError code={code} status={status}" in caplog.text
    assert f"category={category}" in caplog.text
    assert "model=gemini-test-model" in caplog.text
    assert "message=Safe diagnostic message" in caplog.text
