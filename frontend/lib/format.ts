import type { AvailabilityStatus, TicketCategory } from "@/types";

export const STATUS_LABELS: Record<AvailabilityStatus, string> = {
  available: "Tersedia",
  sold_out: "Habis",
  not_open: "Belum dibuka",
  unknown: "Tidak diketahui",
  unavailable: "Tidak tersedia",
  cancelled: "Dibatalkan",
};

export const STATUS_COLORS: Record<AvailabilityStatus, "emerald" | "rose" | "amber" | "sky" | "slate" | "zinc"> = {
  available: "emerald",
  sold_out: "rose",
  not_open: "amber",
  unknown: "sky",
  unavailable: "slate",
  cancelled: "zinc",
};

export const CATEGORY_LABELS: Record<TicketCategory, string> = {
  video_call: "Video Call",
  meet_greet: "Meet & Greet",
  two_shot: "Two Shot",
};

export const CATEGORY_COLORS = ["#34d399", "#f472b6", "#fbbf24"] as const;

export function labelCategory(cat: string): string {
  return CATEGORY_LABELS[cat as TicketCategory] ?? cat;
}

export function labelStatus(status: string): string {
  return STATUS_LABELS[status as AvailabilityStatus] ?? status;
}

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "–";
  return new Intl.NumberFormat("id-ID").format(value);
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "–";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString("id-ID", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatDateShort(value: string | null | undefined): string {
  if (!value) return "–";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString("id-ID", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function timeAgo(value: string | null | undefined): string {
  if (!value) return "–";
  const then = new Date(value).getTime();
  if (Number.isNaN(then)) return value;
  const seconds = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (seconds < 60) return `${seconds}s lalu`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} mnt lalu`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} jam lalu`;
  const days = Math.floor(hours / 24);
  return `${days} hari lalu`;
}

export function fieldLabel(field: string): string {
  const map: Record<string, string> = {
    status: "Status",
    tickets_remaining: "Sisa tiket",
    new_event: "Acara baru",
    schedule: "Jadwal",
  };
  return map[field] ?? field;
}

export function fillPercent(remaining: number | null, quota: number | null): number | null {
  if (remaining === null || quota === null || quota <= 0) return null;
  return Math.min(100, Math.max(0, Math.round((remaining / quota) * 100)));
}