import type { ReactNode } from "react";

interface Props {
  title: string;
  subtitle?: string;
  action?: ReactNode;
}

export function TopBar({ title, subtitle, action }: Props) {
  return (
    <header className="sticky top-0 z-30 flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3 shadow-sm">
      <div className="flex items-baseline gap-3">
        <span className="rounded bg-[#0a66c2] px-2 py-0.5 text-lg font-bold text-white">in</span>
        <h1 className="text-lg font-semibold text-slate-800">{title}</h1>
        {subtitle && <span className="text-sm text-slate-500">{subtitle}</span>}
      </div>
      {action}
    </header>
  );
}
