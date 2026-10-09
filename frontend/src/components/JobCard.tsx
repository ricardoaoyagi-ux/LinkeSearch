import type { Job } from "@/types/job";
import { isApplied, isViewed, relativeTime } from "@/lib/jobStatus";
import { ScoreBadge } from "./ScoreBadge";
import { StatusBadge } from "./StatusBadge";

interface Props {
  job: Job;
  selected: boolean;
  onSelect: (job: Job) => void;
}

export function JobCard({ job, selected, onSelect }: Props) {
  const viewed = isViewed(job);
  const applied = isApplied(job);
  return (
    <li>
      <button
        type="button"
        onClick={() => onSelect(job)}
        className={`w-full border-b border-l-4 border-b-slate-200 px-4 py-3 text-left transition ${
          selected ? "border-l-[#0a66c2] bg-blue-50" : "border-l-transparent hover:bg-slate-50"
        } ${job.ignored_at ? "opacity-50" : viewed && !selected ? "opacity-75" : ""}`}
      >
        <div className="mb-1 flex flex-wrap gap-1.5">
          {job.triage_score !== null && <ScoreBadge score={job.triage_score} />}
          {job.ignored_at && <StatusBadge kind={job.triage_action === "ignored" ? "ignoredByTriage" : "ignored"} />}
          {job.saved_at && <StatusBadge kind="saved" />}
          {applied && <StatusBadge kind="applied" />}
          <StatusBadge kind={viewed ? "viewed" : "notViewed"} />
        </div>
        <p className={`leading-snug text-[#0a66c2] ${viewed ? "font-medium" : "font-bold"}`}>{job.title}</p>
        <p className="text-sm text-slate-800">{job.company}</p>
        <p className="text-sm text-slate-500">
          {job.location}
          {job.workplace_type && ` (${job.workplace_type})`}
        </p>
        <p className="mt-1 text-xs font-semibold text-green-700">
          {job.posted_at
            ? `${job.posted_label.startsWith("Reposted") ? "Repostada" : "Postada"} ${relativeTime(job.posted_at)}`
            : "Data de postagem desconhecida"}
          {job.is_easy_apply && <span className="ml-2 font-normal text-slate-500">· Easy Apply</span>}
        </p>
      </button>
    </li>
  );
}
