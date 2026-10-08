import type { ReactNode } from "react";

interface Props {
  message?: string;
  detail?: string;
  action?: ReactNode;
}

export function LoadingOverlay({ message = "Carregando informações...", detail, action }: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" role="status" aria-live="polite">
      <div className="flex max-w-md min-w-72 flex-col items-center gap-3 rounded-xl bg-white px-10 py-8 text-center shadow-2xl">
        <span className="hourglass text-5xl" aria-hidden>
          ⏳
        </span>
        <p className="text-lg font-semibold text-slate-800">{message}</p>
        {detail && <p className="text-sm text-slate-500">{detail}</p>}
        {action}
      </div>
    </div>
  );
}
