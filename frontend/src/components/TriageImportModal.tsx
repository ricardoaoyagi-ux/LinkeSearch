"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { TriageImportReport } from "@/types/job";
import { Button } from "./Button";
import { Modal } from "./Modal";

interface Props {
  onClose: () => void;
}

export function TriageImportModal({ onClose }: Props) {
  const [text, setText] = useState("");
  const [fileName, setFileName] = useState<string | null>(null);
  const [report, setReport] = useState<TriageImportReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const loadFile = async (file: File | undefined) => {
    if (!file) return;
    setFileName(file.name);
    setText(await file.text());
    setReport(null);
  };

  const runImport = async () => {
    setBusy(true);
    setError(null);
    try {
      setReport(await api.triageImport(text));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      title="Importar resultado da triagem"
      onClose={onClose}
      wide
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Fechar
          </Button>
          <Button onClick={runImport} disabled={busy || !text.trim()}>
            {busy ? "Importando..." : "Importar"}
          </Button>
        </>
      }
    >
      <div className="space-y-3 text-sm text-slate-700">
        <p>
          Envie o arquivo <code>resultado_triagem_*.json</code> gerado pelo ChatGPT ou cole a resposta abaixo. Pode ser
          um arquivo com todas as vagas ou um lote por vez — reimportar só atualiza.
        </p>
        <label className="inline-flex cursor-pointer items-center gap-2 rounded-full border border-[#0a66c2] px-4 py-1.5 font-semibold text-[#0a66c2] hover:bg-blue-50">
          📎 Escolher arquivo
          <input
            type="file"
            accept=".json,.txt,application/json,text/plain"
            className="hidden"
            onChange={(e) => loadFile(e.target.files?.[0])}
          />
        </label>
        {fileName && <span className="ml-2 text-xs text-slate-500">{fileName}</span>}
        <textarea
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            setFileName(null);
            setReport(null);
          }}
          placeholder='[{"job_id": "...", "aderencia": 82, "salario_min": 18000, ...}]'
          rows={8}
          className="w-full rounded-md border border-slate-300 p-2 font-mono text-xs"
        />

        {error && <p className="rounded-md bg-red-50 p-3 text-red-700">⚠ {error}</p>}
        {report && <ImportReportView report={report} />}
      </div>
    </Modal>
  );
}

function ImportReportView({ report }: { report: TriageImportReport }) {
  const problems = report.not_found.length + report.invalid.length + report.duplicates.length;
  return (
    <div className="space-y-2 rounded-lg border border-green-300 bg-green-50 p-4 text-green-950">
      <p className="font-semibold">
        ✔ {report.imported} de {report.total_items} vagas importadas
      </p>
      <ul className="space-y-0.5">
        <li>
          🚫 {report.ignored} ignoradas (aderência ≤ {report.threshold}%)
        </li>
        {report.blocked > 0 && <li>⛔ {report.blocked} de empresas bloqueadas (sempre ignoradas)</li>}
        <li>
          👀 {report.kept} mantidas para você avaliar (&gt; {report.threshold}%)
        </li>
        {report.manual > 0 && <li>✋ {report.manual} já marcadas por você — só receberam a nota</li>}
      </ul>
      {problems > 0 && (
        <div className="mt-2 rounded-md bg-amber-50 p-3 text-amber-900">
          {report.not_found.length > 0 && <p>Não encontradas nesta memória: {report.not_found.join(", ")}</p>}
          {report.duplicates.length > 0 && <p>Repetidas no arquivo (usada a 1ª): {report.duplicates.join(", ")}</p>}
          {report.invalid.map((item) => (
            <p key={`${item.posicao}-${item.job_id ?? ""}`}>
              Item {item.posicao}
              {item.job_id ? ` (${item.job_id})` : ""}: {item.motivo}
            </p>
          ))}
        </div>
      )}
      {report.missing.length > 0 && (
        <div className="mt-2 rounded-md bg-amber-50 p-3 text-amber-900">
          <p className="font-semibold">Vagas dos lotes ainda sem nota — peça ao ChatGPT só estas:</p>
          {report.missing.map((m) => (
            <p key={`${m.semana}-${m.lote}`} className="break-all">
              Lote {String(m.lote).padStart(2, "0")}: {m.job_ids.join(", ")}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
