const STYLES = {
  viewed: "bg-amber-100 text-amber-800 border-amber-300",
  notViewed: "bg-blue-100 text-blue-800 border-blue-300",
  applied: "bg-green-100 text-green-800 border-green-400",
  ignored: "bg-slate-200 text-slate-600 border-slate-400",
  saved: "bg-violet-100 text-violet-800 border-violet-400",
} as const;

const LABELS = {
  viewed: "👁 VISUALIZADA",
  notViewed: "● NOVA",
  applied: "✅ APPLY CLICADO",
  ignored: "🚫 IGNORADA",
  saved: "★ SALVA",
} as const;

export function StatusBadge({ kind }: { kind: keyof typeof STYLES }) {
  return (
    <span className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-bold tracking-wide ${STYLES[kind]}`}>
      {LABELS[kind]}
    </span>
  );
}
