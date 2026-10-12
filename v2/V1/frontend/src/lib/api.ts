import type {
  ChatResponse,
  DoctorDirectory,
  HealthStatus,
  InsightsResponse,
  KnowledgeSource,
  LanguageChoice,
  PeriodInput,
  PeriodRecord,
  SymptomCatalogueItem,
  SymptomInput,
  SymptomRecord,
  TrackerSummary,
} from "./types";

export class ApiError extends Error {
  status: number;
  fieldErrors: Record<string, string>;

  constructor(status: number, message: string, fieldErrors: Record<string, string> = {}) {
    super(message);
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

const BASE = import.meta.env.VITE_API_BASE ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiError(0, "Cannot reach the SakhiSahay server. Is the backend running?");
  }
  if (response.status === 204) return undefined as T;
  const text = await response.text();
  const body = text ? safeJson(text) : null;
  if (!response.ok) {
    const fieldErrors: Record<string, string> = {};
    if (body && Array.isArray(body.errors)) {
      for (const e of body.errors) fieldErrors[e.field || "_"] = e.message;
    }
    const detail = typeof body?.detail === "string" ? body.detail : response.statusText;
    throw new ApiError(response.status, detail || "Request failed", fieldErrors);
  }
  return body as T;
}

function safeJson(text: string) {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

export const api = {
  health: () => request<HealthStatus>("/api/health"),

  summary: () => request<TrackerSummary>("/api/tracker/summary"),
  symptomCatalogue: () => request<SymptomCatalogueItem[]>("/api/tracker/symptom-catalogue"),

  periods: () => request<PeriodRecord[]>("/api/tracker/periods"),
  createPeriod: (data: PeriodInput) => request<PeriodRecord>("/api/tracker/periods", { method: "POST", body: JSON.stringify(data) }),
  updatePeriod: (id: string, data: PeriodInput) =>
    request<PeriodRecord>(`/api/tracker/periods/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deletePeriod: (id: string) => request<void>(`/api/tracker/periods/${id}`, { method: "DELETE" }),

  symptoms: () => request<SymptomRecord[]>("/api/tracker/symptoms"),
  createSymptom: (data: SymptomInput) => request<SymptomRecord>("/api/tracker/symptoms", { method: "POST", body: JSON.stringify(data) }),
  updateSymptom: (id: string, data: SymptomInput) =>
    request<SymptomRecord>(`/api/tracker/symptoms/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteSymptom: (id: string) => request<void>(`/api/tracker/symptoms/${id}`, { method: "DELETE" }),
  deleteAllData: () => request<{ periods_deleted: number; symptoms_deleted: number }>("/api/tracker/all", { method: "DELETE" }),

  insights: () => request<InsightsResponse>("/api/insights"),

  chat: (question: string, language: LanguageChoice, includeTrackerContext: boolean) =>
    request<ChatResponse>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ question, language, include_tracker_context: includeTrackerContext }),
    }),

  knowledgeSources: () => request<KnowledgeSource[]>("/api/knowledge/sources"),
  doctors: () => request<DoctorDirectory>("/api/doctors"),
};
