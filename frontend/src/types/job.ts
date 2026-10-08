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
  status: TaskStatus;
  message: string;
  pages_read: number;
  jobs_found: number;
  new_jobs: number;
  updated_jobs: number;
  week: string | null;
  error: string | null;
}
