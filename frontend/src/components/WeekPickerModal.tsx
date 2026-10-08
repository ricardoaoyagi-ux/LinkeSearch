"use client";

import { useState } from "react";
import type { MemoryFile } from "@/types/job";
import { Button } from "./Button";

interface Props {
  title: string;
  files: MemoryFile[];
  confirmLabel: string;
  danger?: boolean;
  onConfirm: (week: string) => void;
  onClose: () => void;
}

export function WeekPickerModal({ title, files, confirmLabel, danger, onConfirm, onClose }: Props) {
  const [selected, setSelected] = useState(files[0]?.week ?? "");
  const [confirming, setConfirming] = useState(false);
  const chosen = files.find((f) => f.week === selected);

  const handleConfirm = () => {
    if (!selected) return;
    if (danger && !confirming) {
      setConfirming(true);
      return;
    }
    onConfirm(selected);
  };

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div
        className="w-[28rem] rounded-xl bg-white p-6 shadow-2xl"
        role="dialog"
        aria-modal
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="mb-4 text-xl font-semibold text-slate-800">{title}</h2>
        <ul className="mb-5 max-h-80 space-y-2 overflow-y-auto">
          {files.map((f) => (
            <li key={f.week}>
              <label
                className={`flex cursor-pointer items-center justify-between rounded-lg border px-4 py-3 ${
                  selected === f.week ? "border-[#0a66c2] bg-blue-50" : "border-slate-200 hover:bg-slate-50"
                }`}
              >
                <span className="flex items-center gap-3">
                  <input
                    type="radio"
                    name="week"
                    checked={selected === f.week}
                    onChange={() => {
                      setSelected(f.week);
                      setConfirming(false);
                    }}
                  />
                  <span>
                    <span className="block font-medium text-slate-800">{f.label}</span>
                    <span className="block text-xs text-slate-500">vagas_{f.week}.db</span>
                  </span>
                </span>
                <span className="text-sm text-slate-600">{f.job_count} vagas</span>
              </label>
            </li>
          ))}
        </ul>
        {confirming && chosen && (
          <p className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
            Excluir definitivamente a <strong>{chosen.label}</strong> ({chosen.job_count} vagas)? Clique novamente para confirmar.
          </p>
        )}
        <div className="flex justify-end gap-3">
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button variant={danger ? "danger" : "primary"} disabled={!selected} onClick={handleConfirm}>
            {confirming ? "Confirmar exclusão" : confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
