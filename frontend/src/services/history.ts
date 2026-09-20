import { AssistantResponse, AssistantToolCall } from "./api";

export const HISTORY_STORAGE_KEY = "ai-business-process-assistant.history.v1";
export const HISTORY_LIMIT = 25;
export const HISTORY_UPDATED_EVENT = "assistant-history-updated";

export type HistoryStatus = "success" | "failed";
export type HistoryRecord = {
  id: string;
  timestamp: string;
  request: string;
  answer: string;
  tools_used: string[];
  tool_calls: AssistantToolCall[];
  total_execution_time_ms: number;
  model: string;
  status: HistoryStatus;
  error_category?: string;
};

function isRecord(value: unknown): value is HistoryRecord {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<HistoryRecord>;
  return typeof item.id === "string" && typeof item.timestamp === "string" && typeof item.request === "string" && typeof item.answer === "string" && Array.isArray(item.tools_used) && Array.isArray(item.tool_calls) && typeof item.total_execution_time_ms === "number" && typeof item.model === "string" && (item.status === "success" || item.status === "failed");
}

export function getHistory(): HistoryRecord[] {
  try {
    const raw = localStorage.getItem(HISTORY_STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter(isRecord).slice(0, HISTORY_LIMIT) : [];
  } catch { return []; }
}

function save(records: HistoryRecord[]) {
  localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(records.slice(0, HISTORY_LIMIT)));
  window.dispatchEvent(new Event(HISTORY_UPDATED_EVENT));
}

export function addSuccessfulHistory(request: string, response: AssistantResponse) {
  const record: HistoryRecord = {
    id: crypto.randomUUID(), timestamp: new Date().toISOString(), request,
    answer: response.answer, tools_used: [...response.tools_used],
    tool_calls: response.tool_calls.map((call) => ({ ...call, arguments: { ...call.arguments } })),
    total_execution_time_ms: response.total_execution_time_ms, model: response.model, status: "success",
  };
  save([record, ...getHistory()]);
  return record;
}

export function addFailedHistory(request: string, errorCategory: string) {
  const record: HistoryRecord = {
    id: crypto.randomUUID(), timestamp: new Date().toISOString(), request, answer: "",
    tools_used: [], tool_calls: [], total_execution_time_ms: 0, model: "", status: "failed",
    error_category: errorCategory,
  };
  save([record, ...getHistory()]);
  return record;
}

export function clearHistory() { localStorage.removeItem(HISTORY_STORAGE_KEY); window.dispatchEvent(new Event(HISTORY_UPDATED_EVENT)); }

