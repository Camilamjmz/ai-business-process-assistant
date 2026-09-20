# Phase 3 Agent Architecture

## Purpose

The Gemini business assistant translates one natural-language request into a concise answer grounded in deterministic analytics. Gemini selects tools and writes the final explanation; Python remains responsible for validation, calculations, data access, and execution control.

## Request flow

```text
POST /api/assistant/query
  -> validate one user message
  -> send message, system policy, and allow-listed schemas to Gemini
  -> receive zero or more function calls
  -> validate names and arguments in the tool registry
  -> execute deterministic read-only tools
  -> return structured function results to Gemini
  -> repeat for at most five tool rounds
  -> return final answer, call metadata, and sanitized activity events
```

The service uses the official `google-genai` SDK with automatic function calling disabled. Manual execution makes the tool boundary, timing, failures, and loop limit observable and testable.

## Grounding policy

The system instruction requires tools for factual claims about sales, revenue, orders, customers, products, inventory, suppliers, and reorder priorities. It prohibits invented or estimated business values and distinguishes observed evidence from recommendations. Reorder questions should use the deterministic reorder tool.

Only ten tools in `tool_registry.py` are available. Each has an explicit name, purpose, JSON parameter schema, adapter, and activity label. Unknown tools, unexpected fields, missing required fields, invalid dates, and invalid limits are rejected before analytics execute.

Tool results are added to the current Gemini request history as structured function responses. The external response exposes the final answer and sanitized metadata, not raw hidden reasoning.

## Safety bound and failures

The agent supports multiple calls in one model turn and multiple sequential tool rounds. The maximum is five tool-execution rounds. A sixth request fails cleanly instead of entering an infinite loop.

- Missing API key: assistant endpoint returns `503`; the rest of the app still starts.
- Invalid HTTP body: FastAPI returns `422`.
- Gemini failure, invalid tool request, or exhausted loop: sanitized `502`.
- Unexpected server error: sanitized `500`.
- Deterministic tool failures are represented to Gemini without stack traces or internal exception details.

API keys and raw environment variables are never placed in prompts, logs, activity events, tool records, or HTTP errors.

## Data access and privacy

Gemini cannot read files, paths, CSV rows, environment variables, or arbitrary Python functions. Only registry adapters call the analytics layer. Gemini receives the current user message, tool declarations, requested tool results, and minimal request history.

The local datasets are synthetic and contain no real personal or company data.

## Current limitations

- One user message per request; no persistent memory or conversation database
- Text input and text output only
- Read-only analytics; no inventory changes, purchasing, supplier contact, or email
- No streaming response
- No frontend assistant integration in Phase 3
- No complex hallucination detector; grounding uses policy, a restricted tool surface, structured results, and testable traces

