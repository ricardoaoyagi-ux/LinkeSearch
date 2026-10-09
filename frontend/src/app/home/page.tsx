"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/Button";
import { LoadingOverlay } from "@/components/LoadingOverlay";
import { TopBar } from "@/components/TopBar";
import { TriageImportModal } from "@/components/TriageImportModal";
import { TriagePrepareModal } from "@/components/TriagePrepareModal";
import { WeekPickerModal } from "@/components/WeekPickerModal";
import { useScanTask } from "@/hooks/useScanTask";
import { api } from "@/lib/api";
import { formatDateTime, hoursSince } from "@/lib/jobStatus";
import { session } from "@/lib/session";
import { formatWeek, rangeOptions } from "@/lib/week";
import type { StorageStatus, TaskState } from "@/types/job";

type Modal = "read" | "delete" | "triagePick" | "triageImport" | null;

export default function HomePage() {
  const router = useRouter();
  const [status, setStatus] = useState<StorageStatus | null>(null);
  const [rangeHours, setRangeHours] = useState(24);
  const [modal, setModal] = useState<Modal>(null);
  const [busy, setBusy] = useState<string | null>("Carregando informações...");
  const [error, setError] = useState<string | null>(null);
  const [triageWeek, setTriageWeek] = useState<string | null>(null);
  const [triageMessage, setTriageMessage] = useState<string | null>(null);

  const loadStatus = useCallback(async () => {
    try {
      const s = await api.storage();
      setStatus(s);
      setRangeHours(s.suggested_range_hours);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }, []);

  const openWeek = useCallback((week: string) => router.push(`/jobs?week=${week}`), [router]);
  const onTaskFinished = useCallback(
    (task: TaskState) => {
      if (task.kind === "triage") {
        // Back to the triage window with the outcome and the download links
        setTriageMessage(task.message);
        setTriageWeek(task.week);
        return;
      }
      if (task.week && task.jobs_found > 0) openWeek(task.week);
      else loadStatus();
    },
    [openWeek, loadStatus],
  );
  const scan = useScanTask(onTaskFinished);
  const { resumeIfRunning } = scan;

  useEffect(() => {
    if (!session.isEntered()) {
      router.replace("/");
      return;
    }
    loadStatus();
    resumeIfRunning();
  }, [loadStatus, resumeIfRunning, router]);

  const logout = async () => {
    await api.logout().catch(() => undefined);
    session.logout();
    router.push("/");
  };

  const deleteWeek = async (week: string) => {
    setModal(null);
    setBusy("Removendo memória...");
    try {
      setStatus(await api.deleteWeek(week));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  const startTriage = async (week: string) => {
    setTriageWeek(null);
    setTriageMessage(null);
    setError(null);
    try {
      scan.follow(await api.triagePrepare(week));
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const readWeek = (week: string) => {
    setModal(null);
    setBusy("Carregando informações...");
    openWeek(week);
  };

  const hasFiles = (status?.files.length ?? 0) > 0;
  const hoursSinceRun = hoursSince(status?.last_run_at ?? null);
  const isSunday = new Date().getDay() === 0;
  const currentFile = status?.files.find((f) => f.week === status.current_week);

  return (
    <div className="min-h-screen">
      <TopBar
        title="LinkeSearch"
        action={
          <Button variant="ghost" onClick={logout}>
            ⎋ Deslogar
          </Button>
        }
      />

      {busy && <LoadingOverlay message={busy} />}
      {scan.running && scan.task && (
        <LoadingOverlay
          message={scan.task.kind === "triage" ? "Preparando triagem..." : "Carregando informações..."}
          detail={
            scan.task.kind === "triage"
              ? `${scan.task.message} · ${scan.task.jobs_found} descrições buscadas`
              : `${scan.task.message} · ${scan.task.pages_read} páginas · ${scan.task.jobs_found} vagas lidas · ${scan.task.new_jobs} novas`
          }
          action={
            <Button variant="ghost" className="mt-2 text-sm" onClick={scan.cancel}>
              Cancelar (mantém o que já foi gravado)
            </Button>
          }
        />
      )}
      {modal === "read" && status && (
        <WeekPickerModal
          title="Qual semana deseja consultar?"
          files={status.files}
          confirmLabel="Consultar"
          onConfirm={readWeek}
          onClose={() => setModal(null)}
        />
      )}
      {modal === "triagePick" && status && (
        <WeekPickerModal
          title="Triagem de qual semana?"
          files={status.files}
          confirmLabel="Continuar"
          onConfirm={(week) => {
            setModal(null);
            setTriageMessage(null);
            setTriageWeek(week);
          }}
          onClose={() => setModal(null)}
        />
      )}
      {triageWeek && (
        <TriagePrepareModal
          week={triageWeek}
          lastMessage={triageMessage}
          onStart={startTriage}
          onClose={() => {
            setTriageWeek(null);
            setTriageMessage(null);
          }}
        />
      )}
      {modal === "triageImport" && <TriageImportModal onClose={() => setModal(null)} />}
      {modal === "delete" && status && (
        <WeekPickerModal
          title="Qual memória deseja excluir?"
          files={status.files}
          confirmLabel="Excluir"
          danger
          onConfirm={deleteWeek}
          onClose={() => setModal(null)}
        />
      )}

      <main className="mx-auto mt-10 max-w-3xl space-y-6 px-6">
        {(error || scan.error) && <p className="rounded-md bg-red-50 p-4 text-red-700">{error ?? scan.error}</p>}

        <section className="rounded-2xl bg-white p-6 shadow">
          <h2 className="text-xl font-semibold text-slate-800">🔎 Buscar NOVAS vagas</h2>
          <p className="mt-1 text-sm text-slate-500">
            Executa a busca das suas preferências da aba Jobs do LinkedIn e grava em{" "}
            <strong>
              {status ? `Semana de ${formatWeek(status.current_week)} (vagas_${status.current_week}.db)` : "..."}
            </strong>
            {status &&
              (isSunday || !currentFile
                ? " — novo arquivo da semana."
                : ` — incrementando (${currentFile.job_count} vagas).`)}
          </p>

          {status?.last_run_at && (
            <p className="mt-3 text-sm text-slate-600">
              Última busca: {formatDateTime(status.last_run_at)} (há {Math.floor(hoursSinceRun ?? 0)}h, janela de{" "}
              {status.last_range_hours}h)
            </p>
          )}
          {status && status.suggested_range_hours > 24 && (
            <p className="mt-3 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800">
              ⚠ A última busca foi há mais de 24h. Sugerido ampliar a janela para{" "}
              <strong>{status.suggested_range_hours}h</strong> para cobrir o período ainda não visto.
            </p>
          )}

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <label className="text-sm text-slate-600">
              Janela:&nbsp;
              <select
                value={rangeHours}
                onChange={(e) => setRangeHours(Number(e.target.value))}
                className="rounded-md border border-slate-300 px-3 py-1.5"
              >
                {rangeOptions(status?.suggested_range_hours ?? 24).map((h) => (
                  <option key={h} value={h}>
                    Últimas {h} horas{status && h === status.suggested_range_hours && h > 24 ? " (sugerido)" : ""}
                  </option>
                ))}
              </select>
            </label>
            <Button onClick={() => scan.start(rangeHours)} disabled={!status || scan.running}>
              Buscar NOVAS vagas
            </Button>
          </div>
        </section>

        <section className="grid gap-6 sm:grid-cols-2">
          <div className="rounded-2xl bg-white p-6 shadow">
            <h2 className="text-lg font-semibold text-slate-800">📂 Consultar vagas LIDAS</h2>
            <p className="mt-1 text-sm text-slate-500">Abre uma memória semanal já gravada, sem nova busca.</p>
            <Button className="mt-4" variant="secondary" disabled={!hasFiles} onClick={() => setModal("read")}>
              Consultar vagas LIDAS
            </Button>
          </div>
          <div className="rounded-2xl bg-white p-6 shadow">
            <h2 className="text-lg font-semibold text-slate-800">🗑 Limpar vagas</h2>
            <p className="mt-1 text-sm text-slate-500">Exclui o arquivo de memória de uma semana.</p>
            <Button className="mt-4" variant="danger" disabled={!hasFiles} onClick={() => setModal("delete")}>
              Limpar vagas
            </Button>
          </div>
        </section>

        <section className="rounded-2xl bg-white p-6 shadow">
          <h2 className="text-lg font-semibold text-slate-800">🧮 Triagem por aderência (ChatGPT)</h2>
          <p className="mt-1 text-sm text-slate-500">
            1) <strong>Preparar triagem</strong>: busca, devagar, a descrição das vagas novas e gera lotes de 25 para o
            ChatGPT avaliar com o seu arquivo mestre. 2) <strong>Importar resultado</strong>: grava aderência e
            pretensão salarial; vagas com aderência ≤ 59% são ignoradas automaticamente — as demais ficam para você.
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <Button variant="secondary" disabled={!hasFiles || scan.running} onClick={() => setModal("triagePick")}>
              Preparar triagem
            </Button>
            <Button variant="secondary" disabled={!hasFiles || scan.running} onClick={() => setModal("triageImport")}>
              Importar resultado
            </Button>
          </div>
        </section>

        {status && !hasFiles && (
          <p className="text-center text-sm text-slate-500">Nenhuma memória gravada ainda. Faça a primeira busca.</p>
        )}
      </main>
    </div>
  );
}
