interface StatCardProps {
  label: string;
  value: string | number;
  hint?: string;
  tone?: "default" | "success" | "danger" | "warn" | "dim";
}

const TONES: Record<string, string> = {
  default: "border-slate-800 bg-slate-900/60",
  success: "border-emerald-500/30 bg-emerald-500/5",
  danger: "border-rose-500/30 bg-rose-500/5",
  warn: "border-amber-500/30 bg-amber-500/5",
  dim: "border-slate-800 bg-slate-900/40",
};

export default function StatCard({ label, value, hint, tone = "default" }: StatCardProps) {
  return (
    <div className={`rounded-xl border p-4 ${TONES[tone]}`}>
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-white">{value}</div>
      {hint ? <div className="mt-1 text-xs text-slate-500">{hint}</div> : null}
    </div>
  );
}