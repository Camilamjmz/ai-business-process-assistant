export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
export const MAX_MESSAGE_LENGTH = 4000;

export type AssistantToolCall = { tool_name: string; arguments: Record<string, unknown>; success: boolean; execution_time_ms: number };
export type AssistantActivityEvent = { type: string; label: string; tool_name?: string; success?: boolean };
export type AssistantResponse = {
  answer: string;
  tools_used: string[];
  tool_calls: AssistantToolCall[];
  activity: AssistantActivityEvent[];
  status: string;
  model: string;
  total_execution_time_ms: number;
};
export type HealthResponse = { status: string; service: string };
export type SalesSummary = { start_date: string; end_date: string; total_revenue: number; total_orders: number; total_units: number; average_order_value: number; unique_customers: number };
export type SalesTrendPoint = { period: string; revenue: number; orders: number; units: number };
export type SalesTrend = { start_date: string; end_date: string; granularity: "daily" | "monthly"; points: SalesTrendPoint[] };
export type TopProduct = { product_id: string; product_name: string; category: string; units_sold: number; revenue: number; order_count: number };
export type SalesComparison = { period_a: SalesSummary; period_b: SalesSummary; percentage_changes: { revenue: number | null; orders: number | null; units: number | null; average_order_value: number | null } };
export type InventorySummary = { total_products: number; healthy_products: number; low_stock_products: number; critical_products: number; total_units_in_stock: number; percentage_at_risk: number };
export type InventoryProduct = { product_id: string; product_name: string; category: string; current_stock: number; reorder_level: number; inventory_status: "Healthy" | "Low Stock" | "Critical"; supplier_id: string; supplier_name: string; lead_time_days: number; reliability_score: number };
export type ReorderRecommendation = InventoryProduct & { stock_ratio: number; units_below_reorder_level: number; recent_units_sold: number; recent_revenue: number; priority_score: number; recommendation_reason: string };
export type ReorderResponse = { reference_date: string; recent_period_start: string; recent_period_end: string; recommendations: ReorderRecommendation[] };

export class ApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) { super(message); this.name = "ApiError"; this.status = status; }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try { response = await fetch(`${API_BASE_URL}${path}`, init); }
  catch { throw new ApiError("Unable to connect to the analytics API."); }
  if (!response.ok) {
    const messages: Record<number, string> = {
      400: "The request could not be processed.", 422: "Please check your question and try again.",
      500: "The assistant encountered an unexpected error.", 502: "The AI service is temporarily unavailable.",
      503: "AI service is not configured.",
    };
    throw new ApiError(messages[response.status] || "The request could not be completed.", response.status);
  }
  return response.json() as Promise<T>;
}

export const checkHealth = () => request<HealthResponse>("/health");
export const queryAssistant = (message: string) => request<AssistantResponse>("/api/assistant/query", {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message }),
});

const queryString = (params: Record<string, string | number | undefined>) => {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => { if (value !== undefined && value !== "") search.set(key, String(value)); });
  const value = search.toString();
  return value ? `?${value}` : "";
};

export const getSalesSummary = (start_date?: string, end_date?: string) => request<SalesSummary>(`/api/sales/summary${queryString({ start_date, end_date })}`);
export const getSalesTrend = (start_date?: string, end_date?: string, granularity: "daily" | "monthly" = "monthly") => request<SalesTrend>(`/api/sales/trend${queryString({ start_date, end_date, granularity })}`);
export const getTopProducts = (start_date?: string, end_date?: string, limit = 5) => request<TopProduct[]>(`/api/sales/top-products${queryString({ start_date, end_date, limit })}`);
export const compareSalesPeriods = (period_a_start: string, period_a_end: string, period_b_start: string, period_b_end: string) => request<SalesComparison>(`/api/sales/compare${queryString({ period_a_start, period_a_end, period_b_start, period_b_end })}`);
export const getInventorySummary = () => request<InventorySummary>("/api/inventory/summary");
export const getInventory = () => request<InventoryProduct[]>("/api/inventory");
export const getReorderRecommendations = (limit?: number) => request<ReorderResponse>(`/api/inventory/reorder-recommendations${queryString({ limit })}`);
