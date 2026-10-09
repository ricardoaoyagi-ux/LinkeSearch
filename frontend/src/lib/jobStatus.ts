import type { Job } from "@/types/job";

/** Viewed either on LinkedIn or here. */
export const isViewed = (job: Job) => job.li_viewed || job.local_viewed_at !== null;

/** Apply clicked here, or marked "Applied" by LinkedIn. */
export const isApplied = (job: Job) => job.li_applied || job.apply_clicked_at !== null;

/** About + Apply link already fetched from LinkedIn (loaded on open; an empty About is fetched again). */
export const hasDetail = (job: Job) => Boolean(job.about_html) && job.apply_url !== null;

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

/** 18000 -> "R$ 18.000" (currency from the triage, BRL by default) */
export function formatMoney(value: number | null, currency: string | null): string {
  if (value === null) return "—";
  try {
    return value.toLocaleString("pt-BR", { style: "currency", currency: currency || "BRL", maximumFractionDigits: 0 });
  } catch {
    return `${currency ?? ""} ${value.toLocaleString("pt-BR")}`.trim(); // unknown currency code
  }
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
