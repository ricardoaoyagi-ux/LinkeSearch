"use client";

import DOMPurify from "dompurify";
import { useMemo, useState } from "react";
import type { Job } from "@/types/job";
import { formatDateTime, formatMoney, isApplied, isViewed, relativeTime, safeUrl } from "@/lib/jobStatus";
import { ScoreBadge } from "./ScoreBadge";
import { StatusBadge } from "./StatusBadge";

interface Props {
  job: Job | null;
  loading: boolean;
  error: string | null;
  /** Failure of the last button action (save/ignore), shown under the buttons */
  actionError: string | null;
  onApply: (job: Job) => void;
  onToggleIgnore: (job: Job) => void;
  onToggleSave: (job: Job) => void;
}

// Same size for every action so the four buttons line up in one row
const BUTTON = "inline-flex items-center whitespace-nowrap rounded-full border px-4 py-1.5 text-sm font-semibold";

const ALLOWED_TAGS = ["p", "br", "ul", "ol", "li", "strong", "b", "em", "i", "u", "h3", "h4", "div"];

export function JobDetail({ job, loading, error, actionError, onApply, onToggleIgnore, onToggleSave }: Props) {
  // Kept while browsing the list: once minimized, the next jobs open minimized too
  const [summaryCollapsed, setSummaryCollapsed] = useState(false);
  const aboutHtml = useMemo(
    () => (job?.about_html ? DOMPurify.sanitize(job.about_html, { ALLOWED_TAGS, ALLOWED_ATTR: [] }) : ""),
    [job?.about_html],
  );

  if (!job) {
    return <div className="flex h-full items-center justify-center text-slate-400">Selecione uma vaga na lista</div>;
  }

  const applyUrl = safeUrl(job.apply_url);
  const applied = isApplied(job);

  return (
    // Header stays fixed while the description scrolls; on very short windows (< 640px) the whole
    // panel scrolls instead, so the description is never squeezed out of view.
    <article className="flex h-full flex-col [@media(max-height:640px)]:block [@media(max-height:640px)]:overflow-y-auto">
      <header className="shrink-0 border-b border-slate-200 px-6 pt-5 pb-4 shadow-sm">
        <p className="text-sm text-slate-700">{job.company}</p>
        <h2 className="mt-0.5 text-2xl font-semibold text-slate-900">{job.title}</h2>
        <div className="mt-1.5 flex flex-wrap items-center gap-2 text-sm text-slate-500">
          <span>
            {job.location}
            {job.workplace_type && ` · ${job.workplace_type}`}
          </span>
          {job.ignored_at && <StatusBadge kind={job.triage_action === "ignored" ? "ignoredByTriage" : "ignored"} />}
          {job.saved_at && <StatusBadge kind="saved" />}
          {applied && <StatusBadge kind="applied" />}
          <StatusBadge kind={isViewed(job) ? "viewed" : "notViewed"} />
        </div>

        {job.triage_score !== null && (
          <div className="mt-3 rounded-lg border border-slate-200 px-3 py-2 text-sm">
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
              <span className="flex items-center gap-1.5">
                <span className="text-slate-500">Aderência:</span>
                <ScoreBadge score={job.triage_score} />
              </span>
              <span>
                <span className="text-slate-500">Pretensão (CLT):</span>{" "}
                {job.salary_min === null && job.salary_ideal === null && job.salary_max === null ? (
                  // The AI skips the salary research for low fit scores
                  <span className="text-slate-500 italic">não pesquisada (aderência baixa)</span>
                ) : (
                  <>
                    <span className="font-medium">
                      {formatMoney(job.salary_min, job.salary_currency)} /{" "}
                      {formatMoney(job.salary_ideal, job.salary_currency)} /{" "}
                      {formatMoney(job.salary_max, job.salary_currency)}
                    </span>{" "}
                    <span className="text-xs text-slate-400">(mín / ideal / máx)</span>
                  </>
                )}
              </span>
              {job.triage_summary && (
                <button
                  type="button"
                  onClick={() => setSummaryCollapsed((collapsed) => !collapsed)}
                  title={summaryCollapsed ? "Expandir o resumo da triagem" : "Minimizar o resumo da triagem"}
                  aria-label={summaryCollapsed ? "Expandir o resumo da triagem" : "Minimizar o resumo da triagem"}
                  aria-expanded={!summaryCollapsed}
                  className="ml-auto flex h-5 w-5 items-center justify-center rounded border border-slate-300 text-sm leading-none text-slate-500 hover:bg-slate-100"
                >
                  {summaryCollapsed ? "+" : "−"}
                </button>
              )}
            </div>
            {job.triage_summary && !summaryCollapsed && <p className="mt-1 text-slate-600">{job.triage_summary}</p>}
          </div>
        )}

        <dl className="mt-3 flex flex-wrap gap-x-5 gap-y-1 rounded-lg bg-slate-50 px-3 py-2 text-sm">
          <div className="flex gap-1.5">
            <dt className="text-slate-500">Postada:</dt>
            <dd>
              {formatDateTime(job.posted_at)}
              {job.posted_at && <span className="text-slate-500"> ({relativeTime(job.posted_at)})</span>}
              {job.posted_label && <span className="ml-1 text-xs text-slate-400">“{job.posted_label}”</span>}
            </dd>
          </div>
          <div className="flex gap-1.5">
            <dt className="text-slate-500">Localizada:</dt>
            <dd>{formatDateTime(job.found_at)}</dd>
          </div>
          {job.ignored_at && (
            <div className="flex gap-1.5">
              <dt className="text-slate-500">Ignorada:</dt>
              <dd className="text-slate-600">{formatDateTime(job.ignored_at)}</dd>
            </div>
          )}
          {job.apply_clicked_at && (
            <div className="flex gap-1.5">
              <dt className="text-slate-500">Apply clicado:</dt>
              <dd className="font-semibold text-green-700">{formatDateTime(job.apply_clicked_at)}</dd>
            </div>
          )}
          {job.li_applied && <dd className="font-semibold text-green-700">LinkedIn: marcada como Applied</dd>}
        </dl>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          {!applyUrl && loading && (
            <span className={`${BUTTON} border-slate-200 bg-slate-200 text-slate-500`}>
              <span className="hourglass mr-1">⏳</span> Carregando Apply...
            </span>
          )}
          {applyUrl && (
            <a
              href={applyUrl}
              target="_blank"
              rel="noopener noreferrer"
              onClick={() => onApply(job)}
              className={`${BUTTON} border-[#0a66c2] bg-[#0a66c2] text-white hover:bg-[#004182]`}
            >
              {job.is_easy_apply ? "Easy Apply ↗" : "APPLY ↗"}
            </a>
          )}
          <a
            href={safeUrl(job.job_url) ?? "#"}
            target="_blank"
            rel="noopener noreferrer"
            className={`${BUTTON} border-slate-400 text-slate-700 hover:bg-slate-100`}
          >
            Ver no LinkedIn ↗
          </a>
          <button
            type="button"
            onClick={() => onToggleSave(job)}
            title={job.saved_at ? "Remover das vagas salvas" : "Salvar para aplicar depois"}
            className={`${BUTTON} ${
              job.saved_at
                ? "border-violet-500 bg-violet-100 text-violet-800 hover:bg-violet-200"
                : "border-violet-400 text-violet-700 hover:bg-violet-50"
            }`}
          >
            {job.saved_at ? "★ Salva" : "☆ Salvar vaga"}
          </button>
          <button
            type="button"
            onClick={() => onToggleIgnore(job)}
            className={`${BUTTON} ${
              job.ignored_at
                ? "border-[#0a66c2] text-[#0a66c2] hover:bg-blue-50"
                : "border-slate-400 text-slate-600 hover:bg-slate-100"
            }`}
          >
            {job.ignored_at ? "↩ Voltar a listar" : "🚫 Ignorar vaga"}
          </button>
        </div>
        {actionError && <p className="mt-2 text-sm text-red-600">⚠ {actionError}</p>}
      </header>

      {/* key: each job starts with the description scrolled to the top */}
      <section
        key={job.job_id}
        className="min-h-0 flex-1 overflow-y-auto px-6 pt-4 pb-6 [@media(max-height:640px)]:overflow-visible"
      >
        <h3 className="mb-3 text-lg font-semibold">Sobre a vaga</h3>
        {aboutHtml ? (
          <div className="job-about text-slate-800" dangerouslySetInnerHTML={{ __html: aboutHtml }} />
        ) : loading ? (
          <p className="text-slate-500">
            <span className="hourglass mr-2">⏳</span>Carregando descrição do LinkedIn...
          </p>
        ) : (
          <p className="text-slate-400">{error ?? "Descrição não disponível."}</p>
        )}
      </section>
    </article>
  );
}
