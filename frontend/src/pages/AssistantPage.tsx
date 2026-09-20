import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ApiError, AssistantResponse, MAX_MESSAGE_LENGTH, checkHealth, queryAssistant } from "../services/api";
import { addFailedHistory, addSuccessfulHistory } from "../services/history";

type ConversationItem = { id: number; role: "user" | "assistant"; content: string; response?: AssistantResponse };
type ConnectionStatus = "checking" | "connected" | "unavailable";

const examples = [
  "Which products should we reorder this week?",
  "What was total revenue across the dataset?",
  "Which products are currently at risk?",
  "Compare the latest 30 days with the previous 30 days.",
];
const toolLabels: Record<string, string> = {
  get_sales_summary: "Sales Summary", get_top_products: "Top Products", compare_sales_periods: "Sales Period Comparison",
  get_product_sales: "Product Sales", get_inventory_status: "Inventory Status", get_low_stock_products: "Low Stock Products",
  get_inventory_summary: "Inventory Summary", get_supplier_information: "Supplier Information",
  get_suppliers_summary: "Suppliers Summary", get_reorder_recommendations: "Reorder Recommendations",
};
const formatDuration = (ms: number) => ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${Math.round(ms)} ms`;

function StatusBadge({ status }: { status: ConnectionStatus }) {
  const copy = { checking: "Checking", connected: "Connected", unavailable: "Unavailable" }[status];
  const dot = status === "connected" ? "bg-emerald-500" : status === "checking" ? "bg-amber-400" : "bg-rose-500";
  return <div className="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 shadow-card">
    <span className={`h-2 w-2 rounded-full ${dot}`} aria-hidden="true" /><span>Analytics API</span><span className="text-slate-400">/</span><span>{copy}</span>
  </div>;
}

export function AssistantPage() {
  const [message, setMessage] = useState("");
  const [conversation, setConversation] = useState<ConversationItem[]>([]);
  const [latestResponse, setLatestResponse] = useState<AssistantResponse | null>(null);
  const [connection, setConnection] = useState<ConnectionStatus>("checking");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastQuestion, setLastQuestion] = useState("");
  const nextId = useRef(1);
  const conversationEnd = useRef<HTMLDivElement>(null);

  const refreshHealth = async () => {
    setConnection("checking");
    try { const health = await checkHealth(); setConnection(health.status === "ok" ? "connected" : "unavailable"); }
    catch { setConnection("unavailable"); }
  };
  useEffect(() => { void refreshHealth(); }, []);
  useEffect(() => { conversationEnd.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }); }, [conversation, loading]);

  const submitQuestion = async (question: string) => {
    const trimmed = question.trim();
    if (!trimmed || loading || trimmed.length > MAX_MESSAGE_LENGTH) return;
    setLoading(true); setError(null); setLastQuestion(trimmed); setMessage("");
    setConversation((items) => [...items, { id: nextId.current++, role: "user", content: trimmed }]);
    try {
      const response = await queryAssistant(trimmed);
      addSuccessfulHistory(trimmed, response);
      setLatestResponse(response); setConnection("connected");
      setConversation((items) => [...items, { id: nextId.current++, role: "assistant", content: response.answer, response }]);
    } catch (caught) {
      const userMessage = caught instanceof ApiError ? caught.message : "The request could not be completed.";
      const errorCategory = caught instanceof ApiError ? (caught.status === undefined ? "Analytics API unavailable" : `Assistant service HTTP ${caught.status}`) : "Unexpected client error";
      addFailedHistory(trimmed, errorCategory);
      setError(userMessage);
      if (caught instanceof ApiError && caught.status === undefined) setConnection("unavailable");
    } finally { setLoading(false); }
  };
  const handleSubmit = (event: FormEvent) => { event.preventDefault(); void submitQuestion(message); };
  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void submitQuestion(message); }
  };
  const clearConversation = () => { setConversation([]); setLatestResponse(null); setError(null); setLastQuestion(""); setMessage(""); };

  return <section className="space-y-6">
    <header className="flex flex-col gap-4 border-b border-slate-200 pb-6 sm:flex-row sm:items-start sm:justify-between">
      <div><p className="text-sm font-medium text-accent">Grounded business intelligence</p><h2 className="mt-2 text-3xl font-semibold tracking-tight text-ink">AI Business Assistant</h2>
        <p className="mt-3 max-w-2xl text-base leading-7 text-slate-600">Ask questions about sales, inventory, products, suppliers, and restocking decisions.</p></div>
      <StatusBadge status={connection} />
    </header>

    <div className="grid gap-6 xl:grid-cols-[minmax(0,1.55fr)_minmax(320px,0.75fr)]">
      <div className="min-w-0 space-y-5">
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-card">
          <div className="flex min-h-[420px] max-h-[62vh] flex-col overflow-y-auto p-5 sm:p-6" aria-live="polite">
            {!conversation.length && !loading ? <div className="m-auto max-w-xl py-8 text-center"><div className="mx-auto flex h-11 w-11 items-center justify-center rounded-lg bg-slate-950 text-sm font-semibold text-white">AI</div>
              <h3 className="mt-5 text-lg font-semibold text-slate-900">Start with a business question</h3><p className="mt-2 text-sm leading-6 text-slate-500">The assistant selects read-only analytics tools and grounds its answer in deterministic business data.</p></div> : null}
            <div className="space-y-6">
              {conversation.map((item) => <article key={item.id} className={item.role === "user" ? "ml-auto max-w-[85%]" : "max-w-full"}>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">{item.role === "user" ? "You" : "Business Assistant"}</p>
                {item.role === "user" ? <div className="rounded-xl rounded-tr-sm bg-slate-900 px-4 py-3 text-sm leading-6 text-white">{item.content}</div> : <div>
                  <div className="assistant-markdown text-sm leading-7 text-slate-700"><ReactMarkdown remarkPlugins={[remarkGfm]}>{item.content}</ReactMarkdown></div>
                  {item.response ? <p className="mt-4 border-t border-slate-100 pt-3 text-xs text-slate-400">{item.response.model} · {item.response.tools_used.length} {item.response.tools_used.length === 1 ? "tool" : "tools"} · {formatDuration(item.response.total_execution_time_ms)}</p> : null}
                </div>}
              </article>)}
              {loading ? <div className="max-w-md rounded-lg border border-slate-200 bg-slate-50 px-4 py-4"><div className="flex items-center gap-3"><span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-accent" aria-hidden="true" /><div><p className="text-sm font-medium text-slate-700">Processing request...</p><p className="mt-0.5 text-xs text-slate-500">Retrieving business data and preparing a grounded response.</p></div></div></div> : null}
              <div ref={conversationEnd} />
            </div>
          </div>
          <div className="border-t border-slate-200 bg-slate-50/70 p-4 sm:p-5">
            {error ? <div className="mb-4 flex flex-col gap-3 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between" role="alert"><p className="text-sm text-rose-800">{error}</p><button type="button" onClick={() => void submitQuestion(lastQuestion)} disabled={!lastQuestion || loading} className="text-left text-sm font-semibold text-rose-800 underline underline-offset-2 disabled:opacity-50">Retry</button></div> : null}
            <form onSubmit={handleSubmit}><label htmlFor="assistant-message" className="sr-only">Business question</label>
              <textarea id="assistant-message" value={message} onChange={(event) => setMessage(event.target.value.slice(0, MAX_MESSAGE_LENGTH))} onKeyDown={handleKeyDown} disabled={loading} rows={3} maxLength={MAX_MESSAGE_LENGTH} placeholder="Ask about sales, inventory, suppliers, or restocking decisions..." className="w-full resize-none rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm leading-6 text-slate-900 shadow-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-blue-100 disabled:cursor-not-allowed disabled:bg-slate-100" />
              <div className="mt-3 flex items-center justify-between gap-4"><p className="text-xs text-slate-400"><span className="hidden sm:inline">Enter to send · Shift+Enter for a new line · </span>{message.length}/{MAX_MESSAGE_LENGTH}</p><button type="submit" disabled={!message.trim() || loading} className="rounded-md bg-accent px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-300 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-slate-300">{loading ? "Working..." : "Send question"}</button></div>
            </form>
          </div>
        </div>
        <div><p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Example questions</p><div className="grid gap-2 sm:grid-cols-2">{examples.map((example) => <button key={example} type="button" onClick={() => setMessage(example)} disabled={loading} className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-left text-sm leading-5 text-slate-600 shadow-card transition hover:border-slate-300 hover:text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-200 disabled:opacity-50">{example}</button>)}</div></div>
      </div>

      <aside className="space-y-5" aria-label="Agent evidence">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-card"><div className="flex items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Agent Activity</p><h3 className="mt-1 text-base font-semibold text-slate-900">Grounded workflow</h3></div>{conversation.length ? <button type="button" onClick={clearConversation} className="text-xs font-medium text-slate-500 underline-offset-2 hover:text-slate-900 hover:underline focus:outline-none focus:ring-2 focus:ring-blue-200">Clear conversation</button> : null}</div>
          <div className="mt-5 space-y-1">{loading ? <div className="flex gap-3 py-3"><span className="mt-1 h-2.5 w-2.5 rounded-full bg-amber-400" aria-hidden="true" /><div><p className="text-sm font-medium text-slate-700">Processing request</p><p className="mt-1 text-xs text-slate-500">Activity will appear when the response is complete.</p></div></div> : latestResponse ? latestResponse.activity.map((event, index) => <div key={`${event.type}-${event.tool_name || index}`} className="relative flex gap-3 py-3">{index < latestResponse.activity.length - 1 ? <span className="absolute left-[5px] top-6 h-full w-px bg-slate-200" aria-hidden="true" /> : null}<span className={`relative mt-1 h-3 w-3 rounded-full border-2 border-white ring-1 ${event.success === false ? "bg-rose-500 ring-rose-200" : "bg-emerald-500 ring-emerald-200"}`} aria-hidden="true" /><div className="min-w-0"><p className="text-sm font-medium text-slate-700">{event.label}</p>{event.tool_name ? <p className="mt-1 truncate font-mono text-xs text-slate-400">{event.tool_name}</p> : null}</div></div>) : <p className="py-6 text-sm leading-6 text-slate-500">Submit a question to see the sanitized request, tool, and response activity.</p>}</div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-card"><p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Tools Used</p>{latestResponse?.tool_calls.length ? <div className="mt-4 space-y-3">{latestResponse.tool_calls.map((call, index) => <details key={`${call.tool_name}-${index}`} className="group rounded-lg border border-slate-200 bg-slate-50 px-4 py-3"><summary className="cursor-pointer list-none focus:outline-none focus:ring-2 focus:ring-blue-200"><div className="flex items-center justify-between gap-3"><div><p className="text-sm font-semibold text-slate-800">{toolLabels[call.tool_name] || call.tool_name}</p><p className="mt-0.5 font-mono text-[11px] text-slate-400">{call.tool_name}</p></div><div className="text-right"><p className={`text-xs font-semibold ${call.success ? "text-emerald-700" : "text-rose-700"}`}>{call.success ? "Completed" : "Failed"}</p><p className="mt-0.5 text-xs text-slate-400">{formatDuration(call.execution_time_ms)}</p></div></div></summary><div className="mt-3 border-t border-slate-200 pt-3"><p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Technical details</p><pre className="mt-2 overflow-x-auto whitespace-pre-wrap break-words text-xs leading-5 text-slate-600">{JSON.stringify(call.arguments, null, 2)}</pre></div></details>)}</div> : <p className="mt-4 text-sm leading-6 text-slate-500">No analytics tools used in the latest response.</p>}</div>
        {connection === "unavailable" ? <button type="button" onClick={() => void refreshHealth()} className="w-full rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-200">Check API connection</button> : null}
      </aside>
    </div>
  </section>;
}
