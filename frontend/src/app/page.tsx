"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/Button";
import { LoadingOverlay } from "@/components/LoadingOverlay";
import { api } from "@/lib/api";
import { session } from "@/lib/session";

type Phase = "checking" | "ready" | "needsLogin" | "loggingIn" | "error";

export default function LoginPage() {
  const router = useRouter();
  const [phase, setPhase] = useState<Phase>("checking");
  const [error, setError] = useState<string | null>(null);

  const enter = useCallback(() => {
    session.enter();
    router.push("/home");
  }, [router]);

  useEffect(() => {
    api
      .authStatus()
      .then(({ logged_in }) => {
        if (logged_in && !session.justLoggedOut()) enter();
        else setPhase(logged_in ? "ready" : "needsLogin");
      })
      .catch((e: Error) => {
        setError(e.message);
        setPhase("error");
      });
  }, [enter]);

  const connect = async () => {
    setPhase("loggingIn");
    setError(null);
    try {
      const { logged_in } = await api.login();
      if (logged_in) enter();
      else {
        setError("Login não concluído. Tente novamente.");
        setPhase("needsLogin");
      }
    } catch (e) {
      setError((e as Error).message);
      setPhase("needsLogin");
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      {phase === "checking" && <LoadingOverlay message="Verificando sessão do LinkedIn..." />}
      {phase === "loggingIn" && (
        <LoadingOverlay message="Aguardando login..." detail="Faça o login na janela do Chrome que abriu (até 5 min)." />
      )}
      <div className="w-full max-w-md rounded-2xl bg-white p-8 text-center shadow-lg">
        <div className="mb-4 inline-block rounded bg-[#0a66c2] px-3 py-1 text-3xl font-bold text-white">in</div>
        <h1 className="text-2xl font-semibold text-slate-800">LinkeSearch</h1>
        <p className="mt-2 text-sm text-slate-500">Suas vagas do LinkedIn em uma lista única, ordenada e com status claro.</p>

        <div className="mt-8 space-y-3">
          {phase === "ready" && (
            <>
              <p className="text-sm font-medium text-green-700">✔ Sessão do LinkedIn ativa neste computador</p>
              <Button className="w-full" onClick={enter}>
                Entrar
              </Button>
            </>
          )}
          {(phase === "needsLogin" || phase === "loggingIn") && (
            <>
              <p className="text-sm text-slate-600">
                Nenhuma sessão salva. Clique abaixo e faça login no LinkedIn uma única vez (Google SSO funciona). A sessão
                fica salva só nesta máquina.
              </p>
              <Button className="w-full" onClick={connect} disabled={phase === "loggingIn"}>
                Conectar ao LinkedIn
              </Button>
            </>
          )}
          {phase === "error" && (
            <Button className="w-full" variant="secondary" onClick={() => window.location.reload()}>
              Tentar novamente
            </Button>
          )}
          {error && <p className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        </div>
      </div>
    </main>
  );
}
