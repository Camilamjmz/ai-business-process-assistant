"""Bounded Gemini agent loop over the deterministic tool registry."""

import os
from time import perf_counter
from typing import Any

from google import genai
from google.genai import types

from app.agents.prompts import SYSTEM_INSTRUCTION
from app.agents.tool_registry import TOOL_REGISTRY, ToolRegistryError, get_tool_declarations, invoke_tool

DEFAULT_MODEL = "gemini-3.6-flash"
MAX_MESSAGE_LENGTH = 4000
MAX_TOOL_ROUNDS = 5


class AgentConfigurationError(RuntimeError):
    """The AI service is not configured."""


class AgentValidationError(ValueError):
    """The user request is invalid."""


class AgentUpstreamError(RuntimeError):
    """Gemini did not return a usable response."""


class AgentToolError(RuntimeError):
    """Gemini requested a tool outside the allow-list or schema."""


class AgentLoopLimitError(RuntimeError):
    """The bounded tool-execution loop was exhausted."""


def _create_client(api_key: str | None = None):
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise AgentConfigurationError("Gemini AI service is not configured")
    return genai.Client(api_key=key)


def _tool_config() -> types.GenerateContentConfig:
    declarations = [types.FunctionDeclaration(**item) for item in get_tool_declarations()]
    return types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        temperature=0.1,
        tools=[types.Tool(function_declarations=declarations)],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )


def _generate(client: Any, contents: list[Any], model: str):
    try:
        return client.models.generate_content(model=model, contents=contents, config=_tool_config())
    except Exception as exc:
        raise AgentUpstreamError("Gemini service request failed") from exc


def run_business_agent(
    message: str,
    *,
    client: Any | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Answer one message through a bounded, manually controlled Gemini tool loop."""
    if not isinstance(message, str) or not message.strip():
        raise AgentValidationError("message must not be empty")
    message = message.strip()
    if len(message) > MAX_MESSAGE_LENGTH:
        raise AgentValidationError(f"message must not exceed {MAX_MESSAGE_LENGTH} characters")

    active_client = client or _create_client(api_key)
    active_model = model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    started = perf_counter()
    contents: list[Any] = [types.Content(role="user", parts=[types.Part.from_text(text=message)])]
    activity: list[dict[str, Any]] = [{"type": "request_received", "label": "Understanding request"}]
    call_records: list[dict[str, Any]] = []
    tools_used: list[str] = []

    for round_number in range(MAX_TOOL_ROUNDS + 1):
        response = _generate(active_client, contents, active_model)
        function_calls = list(response.function_calls or [])
        if not function_calls:
            answer = (response.text or "").strip()
            if not answer:
                raise AgentUpstreamError("Gemini returned an empty response")
            activity.append({"type": "response_generated", "label": "Generating response"})
            return {
                "answer": answer,
                "tools_used": tools_used,
                "tool_calls": call_records,
                "activity": activity,
                "status": "success",
                "model": active_model,
                "total_execution_time_ms": round((perf_counter() - started) * 1000, 2),
            }
        if round_number >= MAX_TOOL_ROUNDS:
            raise AgentLoopLimitError(f"Tool-call limit of {MAX_TOOL_ROUNDS} rounds exceeded")

        model_content = response.candidates[0].content if response.candidates else None
        if model_content is None:
            raise AgentUpstreamError("Gemini returned an invalid tool-call response")
        contents.append(model_content)
        function_response_parts = []

        for function_call in function_calls:
            tool_name = function_call.name or ""
            arguments = dict(function_call.args or {})
            spec = TOOL_REGISTRY.get(tool_name)
            if spec is None:
                raise AgentToolError(f"Model requested an unavailable tool: {tool_name}")
            activity.append({"type": "tool_call", "label": spec.activity_label, "tool_name": tool_name})
            call_started = perf_counter()
            success = True
            try:
                result = invoke_tool(tool_name, arguments)
                payload = {"result": result}
            except ToolRegistryError as exc:
                raise AgentToolError(str(exc)) from exc
            except (ValueError, KeyError) as exc:
                success = False
                payload = {"error": str(exc).strip("'")}
            except Exception:
                success = False
                payload = {"error": "Tool execution failed"}
            elapsed = round((perf_counter() - call_started) * 1000, 2)
            call_records.append({
                "tool_name": tool_name, "arguments": arguments,
                "success": success, "execution_time_ms": elapsed,
            })
            if tool_name not in tools_used:
                tools_used.append(tool_name)
            activity.append({"type": "tool_result", "label": spec.result_label, "tool_name": tool_name, "success": success})
            function_response_parts.append(types.Part.from_function_response(name=tool_name, response=payload))

        contents.append(types.Content(role="user", parts=function_response_parts))

    raise AgentLoopLimitError(f"Tool-call limit of {MAX_TOOL_ROUNDS} rounds exceeded")
