# Deterministic Analytics Tool Catalog

These functions return JSON-serializable dictionaries and lists. They are the factual analytics layer that a future agent may call; no tool uses an LLM.

In Phase 3, all ten tools are exposed to Gemini through a controlled registry. Agent-facing descriptions explain when each tool applies, while JSON schemas and adapters reject unknown tools or invalid arguments. Gemini never receives direct file or DataFrame access.

## Sales tools

### `get_sales_summary(start_date=None, end_date=None)`

- Purpose: calculate business-level sales KPIs for an inclusive date range.
- Parameters: optional ISO start and end dates; omitted values use the dataset bounds.
- Returns: effective dates, revenue, unique-order count, units, average order value, and unique customers.
- Business question: “How did the business perform during this period?”

### `get_top_products(start_date=None, end_date=None, limit=5)`

- Purpose: rank products by revenue and enrich them with catalog data.
- Parameters: optional inclusive dates and a positive result limit.
- Returns: product identity, category, units, revenue, and unique-order count.
- Business question: “Which products generated the most revenue this quarter?”

### `compare_sales_periods(period_a_start, period_a_end, period_b_start, period_b_end)`

- Purpose: compare two explicit periods, with changes calculated as A relative to B.
- Parameters: start and end dates for periods A and B.
- Returns: both summaries and percentage changes for revenue, orders, units, and average order value. A zero baseline produces `null` rather than an undefined percentage.
- Business question: “How did January perform compared with December?”

### `get_product_sales(product_id, start_date=None, end_date=None)`

- Purpose: calculate sales performance for one known product.
- Parameters: product ID and optional inclusive dates.
- Returns: product metadata, revenue, units, orders, customers, and weighted average unit price.
- Business question: “How has PRD-028 performed this year?”

## Inventory tools

### `get_inventory_status()`

- Purpose: classify all products and add supplier evidence.
- Parameters: none.
- Returns: stock data, inventory status, and supplier metrics for every product.
- Business question: “What is the current inventory position?”

Status rules are applied centrally: **Critical** at or below 50% of reorder level, **Low Stock** above 50% and at or below reorder level, and **Healthy** above reorder level.

### `get_low_stock_products()`

- Purpose: focus attention on Critical and Low Stock products.
- Parameters: none.
- Returns: at-risk products with stock ratio and reorder shortfall.
- Ordering: Critical first, then stock ratio ascending, supplier lead time descending, and product ID ascending.
- Business question: “Which products currently need inventory attention?”

### `get_inventory_summary()`

- Purpose: summarize inventory health.
- Parameters: none.
- Returns: total and status counts, total units, and percentage at risk.
- Business question: “What percentage of the catalog is below its reorder threshold?”

## Supplier tools

### `get_supplier_information(supplier_id)`

- Purpose: retrieve a supplier and the products it supplies.
- Parameters: supplier ID.
- Returns: supplier metrics, product count, and product ID/name list.
- Business question: “Which products depend on SUP-003?”

### `get_suppliers_summary()`

- Purpose: compare supplier coverage and current inventory exposure.
- Parameters: none.
- Returns: supplier metrics, supplied-product count, and at-risk-product count.
- Business question: “Which suppliers support the most products currently at risk?”

## Multi-source tool

### `get_reorder_recommendations(limit=None)`

- Purpose: prioritize at-risk products for replenishment using transparent evidence.
- Parameters: optional positive result limit.
- Returns: the dataset reference date, trailing-30-day window, and ranked recommendations with all score components and a deterministic reason.
- Business question: “Which products should we prioritize for restocking?”

Only Critical and Low Stock products are candidates. The score is:

```text
status points        50 Critical, 25 Low Stock
shortage points      (1 - min(stock ratio, 1)) × 20
demand points        recent units / maximum candidate recent units × 15
lead-time points     lead time / maximum candidate lead time × 10
reliability points   (1 - reliability score) × 5
priority score       sum of the five components
```

Recent demand means the inclusive trailing 30 days ending on `max(sales.date)`. This makes results reproducible and independent of the computer clock. Ties are resolved by product ID.
