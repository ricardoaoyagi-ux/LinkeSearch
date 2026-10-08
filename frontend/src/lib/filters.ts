import type { Job } from "@/types/job";
import { hoursSince, isApplied, isViewed } from "./jobStatus";

export type TriState = "all" | "yes" | "no";

export interface JobFilters {
  viewed: TriState;
  applied: TriState;
  saved: TriState;
  postedWithinHours: number | null;
  hideIgnored: boolean;
  /** Free text matched anywhere in the title (like SQL %text%), ignoring case and accents */
  title: string;
}

export const DEFAULT_FILTERS: JobFilters = {
  viewed: "all",
  applied: "all",
  saved: "all",
  postedWithinHours: null,
  hideIgnored: true,
  title: "",
};

/** "Líder Técnico" -> "lider tecnico" */
export function normalizeText(text: string): string {
  return text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
}

export const POSTED_OPTIONS: { label: string; hours: number | null }[] = [
  { label: "Qualquer data", hours: null },
  { label: "Últimas 2 horas", hours: 2 },
  { label: "Últimas 4 horas", hours: 4 },
  { label: "Últimas 6 horas", hours: 6 },
  { label: "Últimas 12 horas", hours: 12 },
  { label: "Últimas 24 horas", hours: 24 },
];

const matchTri = (state: TriState, value: boolean) => state === "all" || (state === "yes") === value;

export function applyFilters(jobs: Job[], filters: JobFilters, now = Date.now()): Job[] {
  const title = normalizeText(filters.title);
  return jobs.filter((job) => {
    if (filters.hideIgnored && job.ignored_at !== null) return false;
    if (title && !normalizeText(job.title).includes(title)) return false;
    if (!matchTri(filters.viewed, isViewed(job))) return false;
    if (!matchTri(filters.applied, isApplied(job))) return false;
    if (!matchTri(filters.saved, job.saved_at !== null)) return false;
    if (filters.postedWithinHours !== null) {
      const h = hoursSince(job.posted_at, now);
      if (h === null || h > filters.postedWithinHours) return false;
    }
    return true;
  });
}

/** Most recently posted first; jobs without a date go last. */
export function sortByPosted(jobs: Job[]): Job[] {
  return [...jobs].sort((a, b) => {
    if (!a.posted_at) return 1;
    if (!b.posted_at) return -1;
    return new Date(b.posted_at).getTime() - new Date(a.posted_at).getTime();
  });
}
