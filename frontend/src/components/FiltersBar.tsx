"use client";

import { DEFAULT_FILTERS, POSTED_OPTIONS, type JobFilters, type TriState } from "@/lib/filters";
import { Button } from "./Button";

interface Props {
  draft: JobFilters;
  onChange: (filters: JobFilters) => void;
  onApply: () => void;
  onReset: () => void;
  shown: number;
  total: number;
}

const TRI_OPTIONS: { value: TriState; label: string }[] = [
  { value: "all", label: "Todas" },
  { value: "yes", label: "Sim" },
  { value: "no", label: "Não" },
];

function Select({ label, value, onChange, children }: { label: string; value: string; onChange: (v: string) => void; children: React.ReactNode }) {
  return (
    <label className="flex flex-col text-xs font-medium text-slate-600">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-800"
      >
        {children}
      </select>
    </label>
  );
}

export function FiltersBar({ draft, onChange, onApply, onReset, shown, total }: Props) {
  return (
    <form
      className="flex flex-wrap items-end gap-4 border-b border-slate-200 bg-white px-6 py-3"
      onSubmit={(e) => {
        e.preventDefault(); // Enter in the title field applies the filters
        onApply();
      }}
    >
      <label className="flex flex-col text-xs font-medium text-slate-600">
        Título da vaga
        <input
          type="search"
          value={draft.title}
          onChange={(e) => onChange({ ...draft, title: e.target.value })}
          placeholder="ex.: tech lead"
          className="mt-1 w-48 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-800"
        />
      </label>
      <Select label="Visualizada" value={draft.viewed} onChange={(v) => onChange({ ...draft, viewed: v as TriState })}>
        {TRI_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </Select>
      <Select label="Apply clicado" value={draft.applied} onChange={(v) => onChange({ ...draft, applied: v as TriState })}>
        {TRI_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </Select>
      <Select label="Salva" value={draft.saved} onChange={(v) => onChange({ ...draft, saved: v as TriState })}>
        {TRI_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </Select>
      <Select
        label="Data de postagem"
        value={draft.postedWithinHours === null ? "" : String(draft.postedWithinHours)}
        onChange={(v) => onChange({ ...draft, postedWithinHours: v === "" ? null : Number(v) })}
      >
        {POSTED_OPTIONS.map((o) => (
          <option key={o.label} value={o.hours === null ? "" : o.hours}>
            {o.label}
          </option>
        ))}
      </Select>
      <label className="flex items-center gap-2 self-center pt-4 text-sm text-slate-700">
        <input
          type="checkbox"
          checked={draft.hideIgnored}
          onChange={(e) => onChange({ ...draft, hideIgnored: e.target.checked })}
          className="h-4 w-4 accent-[#0a66c2]"
        />
        Não listar vagas ignoradas
      </label>
      <Button type="submit">Aplicar</Button>
      <Button type="button" variant="secondary" onClick={onReset} disabled={JSON.stringify(draft) === JSON.stringify(DEFAULT_FILTERS) && shown === total}>
        Reset
      </Button>
      <span className="ml-auto text-sm text-slate-500">
        {shown} de {total} vagas
      </span>
    </form>
  );
}
