export type FlowLevel = "spotting" | "light" | "medium" | "heavy";

export interface PeriodRecord {
  id: string;
  start_date: string;
  end_date: string | null;
  flow: FlowLevel | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface PeriodInput {
  start_date: string;
  end_date?: string | null;
  flow?: FlowLevel | null;
  notes?: string | null;
}

export interface SymptomRecord {
  id: string;
  record_date: string;
  symptom: string;
  severity: number | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface SymptomInput {
  record_date: string;
  symptom: string;
  severity?: number | null;
  notes?: string | null;
}

export interface SymptomCatalogueItem {
  key: string;
  label: string;
  group: string;
}

export interface TrackerSummary {
  period_count: number;
  symptom_count: number;
  first_record_date: string | null;
  last_period_start: string | null;
  current_period_open: boolean;
}

export type InsightKind = "cycle_length" | "period_duration" | "symptom_frequency" | "symptom_days" | "guidance";

export interface Insight {
  kind: InsightKind;
  title: string;
  statement: string;
  basis: string;
  records_used: number;
  source_url: string | null;
  source_label: string | null;
}

export interface CycleStats {
  logged_periods: number;
  completed_cycles: number;
  cycle_lengths_days: number[];
  average_cycle_length: number | null;
  median_cycle_length: number | null;
  shortest_cycle: number | null;
  longest_cycle: number | null;
  average_period_duration: number | null;
  periods_with_duration: number;
  last_period_start: string | null;
  days_since_last_period_start: number | null;
}

export interface DataRequirement {
  metric: string;
  message: string;
}

export interface InsightsResponse {
  stats: CycleStats;
  insights: Insight[];
  requirements: DataRequirement[];
  generated_from: string;
}

export type LanguageChoice = "auto" | "en" | "hi" | "hinglish";
export type Language = "en" | "hi" | "hinglish";
export type ResponseMode = "llm" | "retrieval_only" | "insufficient_evidence";

export interface SourceRef {
  ref: number;
  source_id: string;
  title: string;
  publisher: string;
  url: string;
  doc_type: string;
  topic: string;
  section: string | null;
  excerpt: string;
  score: number;
  accessed_date: string | null;
  updated_date: string | null;
  cited: boolean;
}

export interface SafetyNotice {
  level: "advisory" | "urgent";
  title: string;
  message: string;
  source_url: string | null;
  source_label: string | null;
}

export interface ChatResponse {
  answer: string;
  mode: ResponseMode;
  language_detected: Language;
  language_used: Language;
  sources: SourceRef[];
  safety: { level: "none" | "advisory" | "urgent"; notices: SafetyNotice[] };
  model: string | null;
  retrieved_count: number;
  best_score: number | null;
  evidence_strength: "none" | "weak" | "moderate" | "strong";
  latency_ms: number;
  fallback_reason: string | null;
  tracker_context_used: boolean;
  disclaimer: string;
}

export interface HealthStatus {
  status: string;
  app_env: string;
  auth_mode: string;
  llm: { provider: string; model: string | null; configured: boolean };
  knowledge: {
    indexed_sources: number;
    embedding_model: string;
    index_ready: boolean;
    chunk_count: number;
    vector_store: string;
  };
}

export interface KnowledgeSource {
  id: string;
  title: string;
  publisher: string;
  url: string;
  doc_type: string;
  topic: string;
  language: string;
  published_date: string | null;
  updated_date: string | null;
  accessed_date: string | null;
  license_note: string | null;
  chunk_count: number;
  status: string;
}

export interface DemoDoctor {
  id: string;
  display_name: string;
  specialty: string;
  focus_areas: string[];
  languages: string[];
  consultation_types: string[];
  city: string;
  is_demo: boolean;
}

export interface DoctorDirectory {
  notice: string;
  doctors: DemoDoctor[];
}
