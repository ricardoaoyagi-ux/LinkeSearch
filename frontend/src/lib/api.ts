import type { Job, StorageStatus, TaskState } from "@/types/job";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { cache: "no-store", ...init });
  } catch {
    throw new ApiError("Backend indisponível. Ele está rodando em 127.0.0.1:8000?", 0);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(body.detail ?? `Erro ${res.status}`, res.status);
  }
  if (res.status === 204) return null as T;
  return res.json() as Promise<T>;
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });

export const api = {
  authStatus: () => request<{ logged_in: boolean }>("/api/auth/status"),
  login: () => post<{ logged_in: boolean }>("/api/auth/login"),
  logout: () => post<{ logged_in: boolean }>("/api/auth/logout"),

  storage: () => request<StorageStatus>("/api/storage"),
  deleteWeek: (week: string) => request<StorageStatus>(`/api/storage/files/${week}`, { method: "DELETE" }),

  startScan: (rangeHours: number) => post<TaskState>("/api/tasks/scan", { range_hours: rangeHours }),
  task: (taskId: string) => request<TaskState>(`/api/tasks/${taskId}`),
  runningTask: () => request<TaskState | null>("/api/tasks/running"),
  cancelTask: (taskId: string) => post<TaskState>(`/api/tasks/${taskId}/cancel`),

  jobs: (week: string, includeIgnored: boolean) =>
    request<Job[]>(`/api/jobs/${week}?include_ignored=${includeIgnored}`),
  ignore: (week: string, jobId: string) => post<Job>(`/api/jobs/${week}/${jobId}/ignore`),
  unignore: (week: string, jobId: string) => request<Job>(`/api/jobs/${week}/${jobId}/ignore`, { method: "DELETE" }),
  save: (week: string, jobId: string) => post<Job>(`/api/jobs/${week}/${jobId}/save`),
  unsave: (week: string, jobId: string) => request<Job>(`/api/jobs/${week}/${jobId}/save`, { method: "DELETE" }),
  jobDetail: (week: string, jobId: string) => post<Job>(`/api/jobs/${week}/${jobId}/detail`),
  markViewed: (week: string, jobId: string) => post<Job>(`/api/jobs/${week}/${jobId}/viewed`),
  markApplyClick: (week: string, jobId: string) => post<Job>(`/api/jobs/${week}/${jobId}/apply-click`),
};
