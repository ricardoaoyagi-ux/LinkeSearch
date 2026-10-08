import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "danger" | "ghost";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-[#0a66c2] text-white hover:bg-[#004182]",
  secondary: "border border-[#0a66c2] text-[#0a66c2] hover:bg-blue-50",
  danger: "bg-red-600 text-white hover:bg-red-700",
  ghost: "text-slate-600 hover:bg-slate-100",
};

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
}

export function Button({ variant = "primary", className = "", ...rest }: Props) {
  return (
    <button
      className={`rounded-full px-5 py-2 font-semibold transition disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-inherit ${VARIANTS[variant]} ${className}`}
      {...rest}
    />
  );
}
