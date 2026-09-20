# Agent Evaluation Methodology

## Purpose

The benchmark measures observable agent behavior: whether Gemini selects the expected deterministic tools, completes requests, and includes stable numeric facts when specified. It does not grade writing style or hidden reasoning.

## Benchmark design

`evaluation/agent_cases.json` contains 20 fixed cases covering sales summaries, period comparison, product performance, inventory health, low-stock identification, suppliers, reorder recommendations, multi-tool questions, capability explanation, and unsupported requests.

Each case declares an ID, category, prompt, expected tool set, whether data tooling is required, and optional stable facts. Expected prose is deliberately not hard-coded.

## Offline validation

```bash
python evaluation/run_agent_evaluation.py --mode offline
```

Offline mode makes no Gemini requests. It verifies:

- required schema fields and types;
- unique case IDs;
- all expected tools exist in the allow-listed registry;
- tool-required cases declare tools;
- selected stable facts still match deterministic analytics.

Normal pytest executes these structural checks and never depends on Gemini availability.

## Live evaluation

With `GEMINI_API_KEY` in the process environment:

```bash
python evaluation/run_agent_evaluation.py --mode live
```

The runner calls the same `run_business_agent` service used by FastAPI. It records status, selected tools, tool count, execution time, and stable-fact matches. It never writes the API key, system prompt, hidden reasoning, or raw environment variables.

Each transient upstream failure receives at most two retries with a short delay. Gemini `503 UNAVAILABLE` responses are classified as service-unavailable cases rather than tool-selection errors. `429 RESOURCE_EXHAUSTED` responses are classified separately as quota exhaustion and are not retried aggressively.

Results are written to `evaluation/results/agent_evaluation_latest.json` and copied to `frontend/public/evaluation/agent_evaluation_latest.json` for read-only display on the Methodology page.

## Metrics

- **Tool Selection Accuracy:** completed cases whose exact tool set matches expectations.
- **Required Tool Usage Rate:** completed cases that used a tool when required.
- **Unexpected Tool Rate:** completed cases containing a tool outside the expected set.
- **Successful Completion Rate:** completed cases divided by all benchmark cases.
- **Numeric Fact Match Rate:** completed answers containing every declared stable fact.
- **Average Tool Calls / Execution Time:** descriptive operational metrics for completed cases.

Logical metrics exclude service-unavailable cases from their denominators. The completion rate retains outages so availability remains visible.

## Limitations

Exact tool-set matching is intentionally strict and may mark a defensible extra tool as incorrect. Substring fact checks are simple and formatting-sensitive. The benchmark is small, synthetic, and not a semantic judge of recommendation quality. Deterministic calculation correctness is established separately through unit tests; this benchmark evaluates LLM routing and grounded response behavior.
