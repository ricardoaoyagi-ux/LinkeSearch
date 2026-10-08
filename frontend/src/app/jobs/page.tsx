"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { Button } from "@/components/Button";
import { FiltersBar } from "@/components/FiltersBar";
import { JobDetail } from "@/components/JobDetail";
import { JobList } from "@/components/JobList";
import { LoadingOverlay } from "@/components/LoadingOverlay";
import { TopBar } from "@/components/TopBar";
import { ApiError, api } from "@/lib/api";
import { DEFAULT_FILTERS, applyFilters, sortByPosted, type JobFilters } from "@/lib/filters";
import { hasDetail, isApplied, isViewed } from "@/lib/jobStatus";
import { session } from "@/lib/session";
import { formatWeek } from "@/lib/week";
import type { Job } from "@/types/job";

/** A bare "Not Found" means the route does not exist: the backend is older than the frontend. */
function actionErrorMessage(e: unknown): string {
  if (e instanceof ApiError && e.status === 404 && e.message === "Not Found") {
    return "O backend está desatualizado. Reinicie o start.ps1 (Ctrl+C e rode de novo).";
  }
  return `Não foi possível concluir a ação: ${(e as Error).message}`;
}

function JobsView() {
  const router = useRouter();
  const week = useSearchParams().get("week") ?? "";
  const [jobs, setJobs] = useState<Job[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<JobFilters>(DEFAULT_FILTERS);
  const [active, setActive] = useState<JobFilters>(DEFAULT_FILTERS);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detailLoading, setDetailLoading] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // The backend leaves ignored jobs out unless the "hide ignored" filter is turned off
  const includeIgnored = !active.hideIgnored;
  useEffect(() => {
    if (!session.isEntered()) {
      router.replace("/");
      return;
    }
    setJobs(null);
    api
      .jobs(week, includeIgnored)
      .then(setJobs)
      .catch((e: Error) => setError(e.message));
  }, [week, includeIgnored, router]);

  const visible = useMemo(() => (jobs ? sortByPosted(applyFilters(jobs, active)) : []), [jobs, active]);
  const selected = jobs?.find((j) => j.job_id === selectedId) ?? null;

  const replaceJob = (updated: Job) =>
    setJobs((list) => list?.map((j) => (j.job_id === updated.job_id ? updated : j)) ?? null);

  const select = async (job: Job) => {
    setSelectedId(job.job_id);
    setDetailError(null);
    setActionError(null);
    if (!job.local_viewed_at) {
      await api
        .markViewed(week, job.job_id)
        .then(replaceJob)
        .catch(() => undefined);
    }
    if (!hasDetail(job)) {
      setDetailLoading(job.job_id);
      try {
        replaceJob(await api.jobDetail(week, job.job_id));
      } catch (e) {
        setDetailError((e as Error).message);
      } finally {
        setDetailLoading((current) => (current === job.job_id ? null : current));
      }
    }
  };

  const apply = (job: Job) => {
    api
      .markApplyClick(week, job.job_id)
      .then(replaceJob)
      .catch(() => undefined);
  };

  /** Neighbour in the current list (below, or above for the last one), opened after a triage action */
  const neighbourOf = (job: Job): Job | null => {
    const index = visible.findIndex((j) => j.job_id === job.job_id);
    return visible[index + 1] ?? visible[index - 1] ?? null;
  };

  const toggleIgnore = async (job: Job) => {
    setActionError(null);
    const next = neighbourOf(job);
    try {
      const updated = job.ignored_at ? await api.unignore(week, job.job_id) : await api.ignore(week, job.job_id);
      replaceJob(updated);
      if (updated.ignored_at && active.hideIgnored) {
        if (next) select(next);
        else setSelectedId(null);
      }
    } catch (e) {
      setActionError(actionErrorMessage(e));
    }
  };

  const toggleSave = async (job: Job) => {
    setActionError(null);
    const next = neighbourOf(job);
    try {
      const updated = job.saved_at ? await api.unsave(week, job.job_id) : await api.save(week, job.job_id);
      replaceJob(updated);
      // Saving moves on to the next job; un-saving stays on the job being reviewed
      if (updated.saved_at && next) select(next);
    } catch (e) {
      setActionError(actionErrorMessage(e));
    }
  };

  const stats = useMemo(() => {
    const list = jobs ?? [];
    const listed = list.filter((j) => j.ignored_at === null);
    return {
      viewed: listed.filter(isViewed).length,
      applied: listed.filter(isApplied).length,
      saved: listed.filter((j) => j.saved_at !== null).length,
      total: listed.length,
    };
  }, [jobs]);

  return (
    <div className="flex h-screen flex-col">
      <TopBar
        title={`Vagas — Semana de ${week ? formatWeek(week) : ""}`}
        subtitle={
          jobs
            ? `${stats.total} vagas · ${stats.viewed} visualizadas · ${stats.saved} salvas · ${stats.applied} com apply`
            : undefined
        }
        action={
          <Button variant="ghost" onClick={() => router.push("/home")}>
            ← Voltar
          </Button>
        }
      />
      {!jobs && !error && <LoadingOverlay />}
      {error && <p className="m-6 rounded-md bg-red-50 p-4 text-red-700">{error}</p>}
      {jobs && (
        <>
          <FiltersBar
            draft={draft}
            onChange={setDraft}
            onApply={() => setActive(draft)}
            onReset={() => {
              setDraft(DEFAULT_FILTERS);
              setActive(DEFAULT_FILTERS);
            }}
            shown={visible.length}
            total={active.hideIgnored ? stats.total : jobs.length}
          />
          <div className="mx-auto flex min-h-0 w-full max-w-7xl flex-1 p-4">
            <aside className="w-[40%] min-w-80 overflow-y-auto rounded-l-lg border border-slate-200 bg-white">
              <JobList jobs={visible} selectedId={selectedId} onSelect={select} />
            </aside>
            <section className="flex-1 overflow-hidden rounded-r-lg border border-l-0 border-slate-200 bg-white">
              <JobDetail
                job={selected}
                loading={selected !== null && detailLoading === selected.job_id}
                error={detailError}
                actionError={actionError}
                onApply={apply}
                onToggleIgnore={toggleIgnore}
                onToggleSave={toggleSave}
              />
            </section>
          </div>
        </>
      )}
    </div>
  );
}

export default function JobsPage() {
  return (
    <Suspense fallback={<LoadingOverlay />}>
      <JobsView />
    </Suspense>
  );
}
