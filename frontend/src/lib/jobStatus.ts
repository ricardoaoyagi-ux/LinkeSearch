import type { Job } from "@/types/job";

/** Viewed either on LinkedIn or here. */
export const isViewed = (job: Job) => job.li_viewed || job.local_viewed_at !== null;

/** Apply clicked here, or marked "Applied" by LinkedIn. */
export const isApplied = (job: Job) => job.li_applied || job.apply_clicked_at !== null;

/** About + Apply link already fetched from LinkedIn (they are loaded on first open). */
export const hasDetail = (job: Job) => job.about_html !== null && job.apply_url !== null;

export function hoursSince(iso: string | null, now = Date.now()): number | null {
  if (!iso) return null;
  return (now - new Date(iso).getTime()) / 3_600_000;
}

export function relativeTime(iso: string | null): string {
  const h = hoursSince(iso);
  if (h === null) return "";
  if (h < 1) return `há ${Math.max(1, Math.round(h * 60))} min`;
  if (h < 48) return `há ${Math.floor(h)}h`;
  return `há ${Math.floor(h / 24)} dias`;
}

export function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

/** Only http(s) links are ever opened. */
export function safeUrl(url: string | null): string | null {
  if (!url) return null;
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" || parsed.protocol === "http:" ? parsed.toString() : null;
  } catch {
    return null;
  }
}
