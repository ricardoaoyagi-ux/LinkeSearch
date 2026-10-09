export interface Job {
  job_id: string;
  week: string;
  title: string;
  company: string;
  location: string;
  workplace_type: string;
  posted_at: string | null;
  posted_label: string;
  job_url: string;
  li_viewed: boolean;
  li_applied: boolean;
  about_html: string | null;
  apply_url: string | null;
  is_easy_apply: boolean | null;
  found_at: string;
  last_seen_at: string;
  local_viewed_at: string | null;
  apply_clicked_at: string | null;
  ignored_at: string | null;
  saved_at: string | null;
  triage_score: number | null;
  salary_min: number | null;
  salary_ideal: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  triage_summary: string | null;
  triaged_at: string | null;
  /** "ignored" when the triage import (not the user) ignored the job */
  triage_action: string | null;
}

export interface MemoryFile {
  week: string;
  label: string;
  job_count: number;
  size_bytes: number;
}

export interface StorageStatus {
  files: MemoryFile[];
  current_week: string;
  last_run_at: string | null;
  last_range_hours: number | null;
  suggested_range_hours: number;
}

export type TaskStatus = "running" | "done" | "cancelled" | "error";

export interface TaskState {
  task_id: string;
  kind: "scan" | "triage";
  status: TaskStatus;
  message: string;
  pages_read: number;
  jobs_found: number;
  new_jobs: number;
  updated_jobs: number;
  week: string | null;
  error: string | null;
}

export interface TriageStatus {
  week: string;
  candidates: number;
  without_about: number;
  fetch_now: number;
  max_per_run: number;
  estimated_minutes: number;
  threshold: number;
  files: string[];
  batch_jobs: number;
  generated_at: string | null;
}

export interface TriageImportReport {
  total_items: number;
  imported: number;
  ignored: number;
  /** jobs from blocked companies (always ignored) */
  blocked: number;
  kept: number;
  manual: number;
  not_found: string[];
  duplicates: string[];
  invalid: { posicao: number; job_id?: string; motivo: string }[];
  missing: { semana: string; lote: number; job_ids: string[] }[];
  threshold: number;
}
