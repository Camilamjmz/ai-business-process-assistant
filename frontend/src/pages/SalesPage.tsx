import { FormEvent, useCallback, useEffect, useState } from "react";
import { ChartCard, EmptyState, ErrorState, KpiCard, LoadingState, MetricDelta, PageHeader, currency, integer } from "../components/analytics/DashboardComponents";
import { PlotlyChart } from "../components/analytics/PlotlyChart";
import { SalesComparison, SalesSummary, SalesTrend, TopProduct, compareSalesPeriods, getSalesSummary, getSalesTrend, getTopProducts } from "../services/api";

const FULL_START = "2025-01-01";
const FULL_END = "2025-12-31";
const comparisonDefaults = { aStart: "2025-12-02", aEnd: "2025-12-31", bStart: "2025-11-02", bEnd: "2025-12-01" };
type SalesData = { summary: SalesSummary; trend: SalesTrend; products: TopProduct[] };

export function SalesPage() {
  const [filters, setFilters] = useState({ start: FULL_START, end: FULL_END });
  const [draft, setDraft] = useState(filters);
  const [data, setData] = useState<SalesData | null>(null);
  const [comparisonDates, setComparisonDates] = useState(comparisonDefaults);
  const [comparison, setComparison] = useState<SalesComparison | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterError, setFilterError] = useState<string | null>(null);

  const loadSales = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const start = filters.start; const end = filters.end;
      const days = Math.round((new Date(end).getTime() - new Date(start).getTime()) / 86400000) + 1;
      const [summary, trend, products] = await Promise.all([getSalesSummary(start, end), getSalesTrend(start, end, days <= 62 ? "daily" : "monthly"), getTopProducts(start, end, 8)]);
      setData({ summary, trend, products });
    } catch { setError("Unable to load sales analytics for this period."); }
    finally { setLoading(false); }
  }, [filters]);
  useEffect(() => { void loadSales(); }, [loadSales]);
  useEffect(() => { void compareSalesPeriods(comparisonDates.aStart, comparisonDates.aEnd, comparisonDates.bStart, comparisonDates.bEnd).then(setComparison).catch(() => setComparison(null)); }, []);

  const applyFilters = (event: FormEvent) => { event.preventDefault(); if (draft.start > draft.end) { setFilterError("Start date must be on or before end date."); return; } setFilterError(null); setFilters(draft); };
  const resetFilters = () => { const full = { start: FULL_START, end: FULL_END }; setDraft(full); setFilters(full); setFilterError(null); };
  const applyComparison = async (event: FormEvent) => { event.preventDefault(); if (comparisonDates.aStart > comparisonDates.aEnd || comparisonDates.bStart > comparisonDates.bEnd) { setFilterError("Each comparison start date must be on or before its end date."); return; } setFilterError(null); try { setComparison(await compareSalesPeriods(comparisonDates.aStart, comparisonDates.aEnd, comparisonDates.bStart, comparisonDates.bEnd)); } catch { setFilterError("Unable to compare these periods."); } };

  return <section className="space-y-6">
    <PageHeader eyebrow="Deterministic sales analytics" title="Sales Analytics" description="Explore revenue, demand, customers, product performance, and period-over-period change." />
    <form onSubmit={applyFilters} className="rounded-xl border border-slate-200 bg-white p-5 shadow-card"><div className="grid items-end gap-4 sm:grid-cols-2 lg:grid-cols-[minmax(150px,1fr)_minmax(150px,1fr)_auto_auto]"><label className="text-sm font-medium text-slate-700">Start date<input type="date" min={FULL_START} max={FULL_END} value={draft.start} onChange={(e) => setDraft({ ...draft, start: e.target.value })} className="mt-2 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-accent focus:outline-none focus:ring-2 focus:ring-blue-100" /></label><label className="text-sm font-medium text-slate-700">End date<input type="date" min={FULL_START} max={FULL_END} value={draft.end} onChange={(e) => setDraft({ ...draft, end: e.target.value })} className="mt-2 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-accent focus:outline-none focus:ring-2 focus:ring-blue-100" /></label><button type="submit" className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white focus:outline-none focus:ring-2 focus:ring-blue-300">Apply</button><button type="button" onClick={resetFilters} className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-200">Reset</button></div>{filterError ? <p className="mt-3 text-sm text-rose-700" role="alert">{filterError}</p> : null}</form>
    {loading ? <LoadingState label="Loading sales analytics..." /> : error || !data ? <ErrorState message={error || "Sales data is unavailable."} onRetry={() => void loadSales()} /> : <>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5"><KpiCard label="Revenue" value={currency.format(data.summary.total_revenue)} /><KpiCard label="Orders" value={integer.format(data.summary.total_orders)} /><KpiCard label="Units Sold" value={integer.format(data.summary.total_units)} /><KpiCard label="Average Order Value" value={currency.format(data.summary.average_order_value)} /><KpiCard label="Unique Customers" value={integer.format(data.summary.unique_customers)} /></div>
      <div className="grid gap-6 xl:grid-cols-2"><ChartCard title="Revenue Over Time" subtitle={`${data.trend.granularity === "daily" ? "Daily" : "Monthly"} revenue for the selected inclusive period.`}>{data.trend.points.length ? <PlotlyChart ariaLabel="Revenue over time line chart" data={[{ type: "scatter", mode: "lines+markers", x: data.trend.points.map((p) => p.period), y: data.trend.points.map((p) => p.revenue), line: { color: "#1f4b7a", width: 3 }, marker: { size: 5 }, hovertemplate: "%{x}<br>$%{y:,.2f}<extra></extra>" }]} layout={{ yaxis: { tickprefix: "$", gridcolor: "#e2e8f0", zeroline: false }, xaxis: { gridcolor: "#f1f5f9" } }} /> : <EmptyState message="No sales occurred during this period." />}</ChartCard>
        <ChartCard title="Top Products" subtitle="Products ranked by deterministic revenue aggregation.">{data.products.length ? <PlotlyChart ariaLabel="Top product revenue bar chart" data={[{ type: "bar", orientation: "h", x: [...data.products].reverse().map((p) => p.revenue), y: [...data.products].reverse().map((p) => p.product_name), marker: { color: "#406b98" }, hovertemplate: "%{y}<br>$%{x:,.2f}<extra></extra>" }]} layout={{ margin: { l: 145, r: 20, t: 16, b: 44 }, xaxis: { tickprefix: "$", gridcolor: "#e2e8f0", zeroline: false }, yaxis: { automargin: true } }} /> : <EmptyState message="No products are available for this period." />}</ChartCard></div>
      <ChartCard title="Product Performance" subtitle="Revenue, demand, and order counts for the selected period."><div className="overflow-x-auto"><table className="w-full min-w-[640px] text-left text-sm"><thead className="border-b border-slate-200 text-xs uppercase tracking-wider text-slate-500"><tr><th className="pb-3">Product</th><th className="pb-3">Category</th><th className="pb-3 text-right">Revenue</th><th className="pb-3 text-right">Units</th><th className="pb-3 text-right">Orders</th></tr></thead><tbody className="divide-y divide-slate-100">{data.products.map((p) => <tr key={p.product_id}><td className="py-3 font-medium text-slate-900">{p.product_name}<span className="ml-2 text-xs text-slate-400">{p.product_id}</span></td><td className="py-3 text-slate-600">{p.category}</td><td className="py-3 text-right">{currency.format(p.revenue)}</td><td className="py-3 text-right">{integer.format(p.units_sold)}</td><td className="py-3 text-right">{integer.format(p.order_count)}</td></tr>)}</tbody></table></div></ChartCard>
    </>}

    <ChartCard title="Period Comparison" subtitle="Percentage change is Period A relative to Period B; signs are shown explicitly."><form onSubmit={applyComparison} className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">{(["aStart", "aEnd", "bStart", "bEnd"] as const).map((key) => <label key={key} className="text-xs font-semibold text-slate-600">{key === "aStart" ? "Period A start" : key === "aEnd" ? "Period A end" : key === "bStart" ? "Period B start" : "Period B end"}<input type="date" value={comparisonDates[key]} onChange={(e) => setComparisonDates({ ...comparisonDates, [key]: e.target.value })} className="mt-1 block w-full rounded-md border border-slate-300 px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-100" /></label>)}<button type="submit" className="self-end rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white focus:outline-none focus:ring-2 focus:ring-blue-300 xl:col-span-2">Compare periods</button></form>{comparison ? <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{(["revenue", "orders", "units", "average_order_value"] as const).map((metric) => <div key={metric} className="rounded-lg bg-slate-50 p-4"><p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{metric.replaceAll("_", " ")}</p><p className="mt-2"><MetricDelta value={comparison.percentage_changes[metric]} /></p><p className="mt-2 text-xs text-slate-500">A: {metric === "revenue" || metric === "average_order_value" ? currency.format(Number(comparison.period_a[metric === "revenue" ? "total_revenue" : "average_order_value"])) : integer.format(Number(comparison.period_a[metric === "orders" ? "total_orders" : "total_units"]))}<br />B: {metric === "revenue" || metric === "average_order_value" ? currency.format(Number(comparison.period_b[metric === "revenue" ? "total_revenue" : "average_order_value"])) : integer.format(Number(comparison.period_b[metric === "orders" ? "total_orders" : "total_units"]))}</p></div>)}</div> : <EmptyState message="Comparison results are unavailable." />}</ChartCard>
  </section>;
}
