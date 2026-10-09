"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { formatDateTime } from "@/lib/jobStatus";
import { formatWeek } from "@/lib/week";
import type { TriageStatus } from "@/types/job";
import { Button } from "./Button";
import { Modal } from "./Modal";

interface Props {
  week: string;
  /** Outcome of the run that just finished, shown on top */
  lastMessage?: string | null;
  onStart: (week: string) => void;
  onClose: () => void;
}

export function TriagePrepareModal({ week, lastMessage, onStart, onClose }: Props) {
  const [status, setStatus] = useState<TriageStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .triageStatus(week)
      .then(setStatus)
      .catch((e: Error) => setError(e.message));
  }, [week]);

  const batchFiles = status?.files.filter((f) => f.includes("_lote_")) ?? [];
  const promptFile = status?.files.find((f) => f.includes("LEIA_PRIMEIRO"));

  return (
    <Modal
      title={`Triagem — Semana de ${formatWeek(week)}`}
      onClose={onClose}
      wide
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Fechar
          </Button>
          <Button onClick={() => onStart(week)} disabled={!status || status.candidates === 0}>
            {status && status.fetch_now > 0 ? "Buscar descrições e gerar lotes" : "Gerar lotes"}
          </Button>
        </>
      }
    >
      {lastMessage && <p className="mb-4 rounded-md bg-blue-50 p-3 text-sm text-blue-900">{lastMessage}</p>}
      {error && <p className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      {!status && !error && <p className="text-slate-500">Carregando...</p>}

      {status && (
        <div className="space-y-4 text-sm text-slate-700">
          <ul className="space-y-1">
            <li>
              <strong>{status.candidates}</strong> vagas novas para triar (sem salva, ignorada, apply ou triagem
              anterior)
            </li>
            <li>
              <strong>{status.without_about}</strong> ainda sem descrição
              {status.fetch_now > 0 && (
                <>
                  {" "}
                  → nesta execução: <strong>{status.fetch_now}</strong> (máx. {status.max_per_run} por vez), cerca de{" "}
                  <strong>{status.estimated_minutes} min</strong>
                </>
              )}
            </li>
          </ul>
          {status.fetch_now > 0 && (
            <p className="rounded-md border border-amber-300 bg-amber-50 p-3 text-amber-900">
              🐢 As descrições são buscadas devagar, com pausas de 4–9 s por vaga e 1–2 min a cada 25, para não chamar a
              atenção do LinkedIn. Evite rodar logo após uma busca de vagas. Se o LinkedIn limitar, a triagem para
              sozinha e mantém o que já buscou.
            </p>
          )}

          {status.files.length > 0 ? (
            <div className="rounded-lg border border-slate-200 p-4">
              <div className="mb-2 flex items-center justify-between">
                <p className="font-semibold text-slate-800">
                  Lotes gerados — {status.batch_jobs} vagas em {batchFiles.length} lotes
                </p>
                <a className="text-sm font-semibold text-[#0a66c2] hover:underline" href={api.triageZipUrl(week)}>
                  ⬇ Baixar todos (.zip)
                </a>
              </div>
              {status.generated_at && (
                <p className="mb-3 text-xs text-slate-500">Gerados em {formatDateTime(status.generated_at)}</p>
              )}
              <ol className="space-y-1">
                {promptFile && (
                  <li>
                    <a className="text-[#0a66c2] hover:underline" href={api.triageFileUrl(week, promptFile)}>
                      📄 {promptFile}
                    </a>{" "}
                    <span className="text-xs text-slate-500">— cole como 1ª mensagem no ChatGPT</span>
                  </li>
                )}
                {batchFiles.map((name) => (
                  <li key={name}>
                    <a className="text-[#0a66c2] hover:underline" href={api.triageFileUrl(week, name)}>
                      🗂 {name}
                    </a>
                  </li>
                ))}
              </ol>
              <p className="mt-3 text-xs text-slate-500">
                No ChatGPT: anexe seu arquivo mestre, envie o prompt e depois um lote por mensagem. Ao final, importe o
                arquivo de resultado em “Importar resultado”.
              </p>
            </div>
          ) : (
            <p className="text-slate-500">Nenhum lote gerado ainda para esta semana.</p>
          )}
        </div>
      )}
    </Modal>
  );
}
