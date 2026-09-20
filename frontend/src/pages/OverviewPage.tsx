import { useCallback, useEffect, useState } from "react";
import { ChartCard, EmptyState, ErrorState, KpiCard, LoadingState, PageHeader, StatusBadge, currency, integer } from "../components/analytics/DashboardComponents";
import { PlotlyChart } from "../components/analytics/PlotlyChart";
import { InventorySummary, ReorderRecommendation, SalesSummary, SalesTrend, TopProduct, getInventorySummary, getReorderRecommendations, getSalesSummary, getSalesTrend, getTopProducts } from "../services/api";

type OverviewData = { sales: SalesSummary; inventory: InventorySummary; trend: SalesTrend; products: TopProduct[]; reorder: ReorderRecommendation[] };

export function OverviewPage() {
  const [data, setData] = useState<OverviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const [sales, inventory, trend, products, reorder] = await Promise.all([getSalesSummary(), getInventorySummary(), getSalesTrend(), getTopProducts(undefined, undefined, 5), getReorderRecommendations(5)]);
      setData({ sales, inventory, trend, products, reorder: reorder.recommendations });
    } catch { setError("Unable to load dashboard data from the analytics API."); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);
  if (loading) return <LoadingState label="Loading operational overview..." />;
  if (error || !data) return <ErrorState message={error || "Dashboard data is unavailable."} onRetry={() => void load()} />;
  const atRisk = data.inventory.low_stock_products + data.inventory.critical_products;

  return <section className="space-y-6">
    <PageHeader eyebrow="Business operations" title="Overview" description={`Full-dataset performance and inventory health from ${data.sales.start_date} through ${data.sales.end_date}.`} />
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <KpiCard label="Total Revenue" value={currency.format(data.sales.total_revenue)} detail="Recognized across all synthetic orders" />
      <KpiCard label="Total Orders" value={integer.format(data.sales.total_orders)} detail={`${integer.format(data.sales.unique_customers)} unique customers`} />
      <KpiCard label="Units Sold" value={integer.format(data.sales.total_units)} detail="Across 40 catalog products" />
      <KpiCard label="Average Order Value" value={currency.format(data.sales.average_order_value)} detail="Revenue per unique order" />
    </div>
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <KpiCard label="Total Products" value={integer.format(data.inventory.total_products)} />
      <KpiCard label="Products At Risk" value={integer.format(atRisk)} detail="Low Stock and Critical" />
      <KpiCard label="Critical Products" value={integer.format(data.inventory.critical_products)} detail="At or below 50% of reorder level" />
      <KpiCard label="Percentage At Risk" value={`${data.inventory.percentage_at_risk.toFixed(1)}%`} />
    </div>
    <div className="grid gap-6 xl:grid-cols-2">
      <ChartCard title="Revenue Trend" subtitle="Monthly revenue across the available business dataset.">
        {data.trend.points.length ? <PlotlyChart ariaLabel="Monthly revenue line chart" data={[{ type: "scatter", mode: "lines+markers", x: data.trend.points.map((p) => p.period), y: data.trend.points.map((p) => p.revenue), line: { color: "#1f4b7a", width: 3 }, marker: { size: 6 }, hovertemplate: "%{x}<br>$%{y:,.2f}<extra></extra>" }]} layout={{ yaxis: { tickprefix: "$", separatethousands: true, gridcolor: "#e2e8f0", zeroline: false }, xaxis: { gridcolor: "#f1f5f9" } }} /> : <EmptyState message="No trend points are available." />}
      </ChartCard>
      <ChartCard title="Top Products" subtitle="Five highest-revenue products across the full period.">
        {data.products.length ? <PlotlyChart ariaLabel="Top products revenue horizontal bar chart" data={[{ type: "bar", orientation: "h", x: [...data.products].reverse().map((p) => p.revenue), y: [...data.products].reverse().map((p) => p.product_name), marker: { color: "#406b98" }, hovertemplate: "%{y}<br>$%{x:,.2f}<extra></extra>" }]} layout={{ margin: { l: 145, r: 20, t: 16, b: 44 }, xaxis: { tickprefix: "$", gridcolor: "#e2e8f0", zeroline: false }, yaxis: { automargin: true } }} /> : <EmptyState message="No product rankings are available." />}
      </ChartCard>
      <ChartCard title="Inventory Health" subtitle="Current product count by deterministic inventory status.">
        <PlotlyChart ariaLabel="Inventory health donut chart" data={[{ type: "pie", hole: 0.62, labels: ["Healthy", "Low Stock", "Critical"], values: [data.inventory.healthy_products, data.inventory.low_stock_products, data.inventory.critical_products], marker: { colors: ["#2f855a", "#d69e2e", "#c2415d"] }, textinfo: "label+value", hovertemplate: "%{label}: %{value}<extra></extra>" }]} layout={{ showlegend: false, margin: { l: 20, r: 20, t: 16, b: 20 } }} />
      </ChartCard>
      <ChartCard title="Reorder Priorities" subtitle="Highest deterministic priority scores; no AI scoring is used.">
        <div className="space-y-3">{data.reorder.map((item, index) => <div key={item.product_id} className="flex items-center gap-4 rounded-lg border border-slate-200 p-3"><span className="w-5 text-sm font-semibold text-slate-400">{index + 1}</span><div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold text-slate-900">{item.product_name}</p><p className="mt-1 text-xs text-slate-500">{item.current_stock} in stock / {item.reorder_level} reorder level</p></div><div className="text-right"><StatusBadge status={item.inventory_status} /><p className="mt-1 text-xs font-semibold text-slate-700">Score {item.priority_score.toFixed(2)}</p></div></div>)}</div>
      </ChartCard>
    </div>
  </section>;
}
