"use client";

import type { ReactNode } from "react";

interface Props {
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  wide?: boolean;
}

export function Modal({ title, onClose, children, footer, wide }: Props) {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className={`flex max-h-[90vh] w-full flex-col rounded-xl bg-white shadow-2xl ${wide ? "max-w-2xl" : "max-w-md"}`}
        role="dialog"
        aria-modal
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="border-b border-slate-200 px-6 py-4 text-xl font-semibold text-slate-800">{title}</h2>
        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-4">{children}</div>
        {footer && <div className="flex justify-end gap-3 border-t border-slate-200 px-6 py-3">{footer}</div>}
      </div>
    </div>
  );
}
