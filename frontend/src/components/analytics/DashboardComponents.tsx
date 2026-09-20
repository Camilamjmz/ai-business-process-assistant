import { ReactNode } from "react";

export const currency = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 });
export const integer = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });

export function PageHeader({ eyebrow, title, description, children }: { eyebrow: string; title: string; description: string; children?: ReactNode }) {
  return <header className="flex flex-col gap-4 border-b border-slate-200 pb-6 sm:flex-row sm:items-start sm:justify-between"><div><p className="text-sm font-medium text-accent">{eyebrow}</p><h2 className="mt-2 text-3xl font-semibold tracking-tight text-ink">{title}</h2><p className="mt-3 max-w-3xl text-base leading-7 text-slate-600">{description}</p></div>{children}</header>;
}

export function KpiCard({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-card"><p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</p><p className="mt-3 text-2xl font-semibold tracking-tight text-slate-900">{value}</p>{detail ? <p className="mt-2 text-xs leading-5 text-slate-500">{detail}</p> : null}</article>;
}

export function ChartCard({ title, subtitle, children, className = "" }: { title: string; subtitle: string; children: ReactNode; className?: string }) {
  return <section className={`min-w-0 rounded-xl border border-slate-200 bg-white p-5 shadow-card ${className}`}><h3 className="text-base font-semibold text-slate-900">{title}</h3><p className="mt-1 text-sm leading-5 text-slate-500">{subtitle}</p><div className="mt-4 min-w-0">{children}</div></section>;
}

export function LoadingState({ label = "Loading analytics..." }: { label?: string }) {
  return <div className="flex min-h-64 items-center justify-center rounded-xl border border-slate-200 bg-white p-8 text-sm text-slate-500"><span className="mr-3 h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-accent" aria-hidden="true" />{label}</div>;
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return <div className="rounded-xl border border-rose-200 bg-rose-50 p-6" role="alert"><h3 className="font-semibold text-rose-900">Analytics unavailable</h3><p className="mt-2 text-sm text-rose-800">{message}</p>{onRetry ? <button type="button" onClick={onRetry} className="mt-4 rounded-md border border-rose-300 bg-white px-4 py-2 text-sm font-semibold text-rose-800 focus:outline-none focus:ring-2 focus:ring-rose-300">Retry</button> : null}</div>;
}

export function EmptyState({ message }: { message: string }) { return <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-sm text-slate-500">{message}</div>; }

export function StatusBadge({ status }: { status: string }) {
  const style = status === "Healthy" ? "bg-emerald-50 text-emerald-800 ring-emerald-200" : status === "Critical" ? "bg-rose-50 text-rose-800 ring-rose-200" : "bg-amber-50 text-amber-800 ring-amber-200";
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${style}`}>{status}</span>;
}

export function MetricDelta({ value }: { value: number | null }) {
  const text = value === null ? "Not available" : `${value > 0 ? "+" : ""}${value.toFixed(2)}%`;
  return <span className="font-semibold text-slate-800">{text}</span>;
}
