import type { Job } from "@/types/job";
import { JobCard } from "./JobCard";

interface Props {
  jobs: Job[];
  selectedId: string | null;
  onSelect: (job: Job) => void;
}

export function JobList({ jobs, selectedId, onSelect }: Props) {
  if (jobs.length === 0) {
    return <p className="p-6 text-center text-slate-500">Nenhuma vaga com esses filtros.</p>;
  }
  return (
    <ul>
      {jobs.map((job) => (
        <JobCard key={job.job_id} job={job} selected={job.job_id === selectedId} onSelect={onSelect} />
      ))}
    </ul>
  );
}
