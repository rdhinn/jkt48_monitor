import type { AvailabilityStatus } from "@/types";
import { STATUS_COLORS, STATUS_LABELS } from "@/lib/format";

const COLOR_CLASSES: Record<string, string> = {
  emerald: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  rose: "bg-rose-500/15 text-rose-300 border-rose-500/30",
  amber: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  sky: "bg-sky-500/15 text-sky-300 border-sky-500/30",
  slate: "bg-slate-500/15 text-slate-300 border-slate-500/30",
  zinc: "bg-zinc-500/15 text-zinc-300 border-zinc-500/30",
};

const DOT_CLASSES: Record<string, string> = {
  emerald: "bg-emerald-400",
  rose: "bg-rose-400",
  amber: "bg-amber-400",
  sky: "bg-sky-400",
  slate: "bg-slate-400",
  zinc: "bg-zinc-400",
};

export default function StatusBadge({ status }: { status: string }) {
  const color = STATUS_COLORS[status as AvailabilityStatus] ?? "slate";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium ${COLOR_CLASSES[color]}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${DOT_CLASSES[color]}`} />
      {STATUS_LABELS[status as AvailabilityStatus] ?? status}
    </span>
  );
}