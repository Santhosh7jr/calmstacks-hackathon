import type { ButtonHTMLAttributes, ReactNode } from "react";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost";
  children: ReactNode;
};

export function Button({
  children,
  className = "",
  variant = "primary",
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`inline-flex items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-bold transition duration-200 disabled:cursor-not-allowed disabled:opacity-50 ${variant === "primary" ? "bg-teal-300 text-slate-950 shadow-lg shadow-teal-950/30 hover:-translate-y-0.5 hover:bg-teal-200" : variant === "secondary" ? "border border-white/15 bg-white/5 text-slate-100 hover:border-teal-300/50 hover:bg-white/10" : "text-slate-400 hover:text-white"} ${className}`.trim()}
      {...props}
    >
      {children}
    </button>
  );
}

export default Button;
