type BadgeProps = {
  children: string;
  tone?: "success" | "warning" | "neutral";
};

export function Badge({ children, tone = "neutral" }: BadgeProps) {
  return (
    <span
      className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.14em] ${tone === "success" ? "border-teal-300/20 bg-teal-300/10 text-teal-200" : tone === "warning" ? "border-amber-300/20 bg-amber-300/10 text-amber-200" : "border-white/10 bg-white/5 text-slate-400"}`}
    >
      {children}
    </span>
  );
}

export default Badge;
