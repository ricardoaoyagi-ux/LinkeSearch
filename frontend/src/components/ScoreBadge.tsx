/** Fit score imported from the triage (green >= 80, amber 60-79, red <= 59). */
export function ScoreBadge({ score }: { score: number }) {
  const style =
    score >= 80
      ? "bg-emerald-600 text-white border-emerald-700"
      : score >= 60
        ? "bg-amber-400 text-amber-950 border-amber-500"
        : "bg-red-100 text-red-800 border-red-300";
  return (
    <span
      className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-bold ${style}`}
      title="Aderência calculada na triagem"
    >
      {score}%
    </span>
  );
}
