"use client";

import { useCallback, useMemo, useState } from "react";
import StatusBadge from "@/components/StatusBadge";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import {
  CATEGORY_LABELS,
  formatDateShort,
  formatNumber,
  labelCategory,
  timeAgo,
} from "@/lib/format";
import type { AvailabilityRow, AvailabilityStatus, Page } from "@/types";

const CATEGORY_KEYS = Object.keys(CATEGORY_LABELS) as string[];
const STATUS_KEYS: AvailabilityStatus[] = [
  "available",
  "sold_out",
  "not_open",
  "unknown",
  "unavailable",
  "cancelled",
];

interface Filters {
  category: string;
  status: string;
  favoritesOnly: boolean;
  q: string;
}

export default function AvailabilityPage() {
  const [filters, setFilters] = useState<Filters>({
    category: "",
    status: "",
    favoritesOnly: false,
    q: "",
  });
  const [debouncedQ, setDebouncedQ] = useState("");

  const buildQuery = useCallback(() => {
    const params = new URLSearchParams({ per_page: "200" });
    if (filters.category) params.set("category", filters.category);
    if (filters.status) params.set("status", filters.status);
    if (filters.favoritesOnly) params.set("favorites_only", "true");
    if (debouncedQ) params.set("member", debouncedQ);
    const qs = params.toString();
    return qs ? `?${qs}` : "";
  }, [filters, debouncedQ]);

  const { data, loading, error, refresh } = useApi<Page<AvailabilityRow>>(
    () => api<Page<AvailabilityRow>>(`/availability${buildQuery()}`),
    15000
  );

  const rows = useMemo(() => data?.items ?? [], [data]);

  const update = (patch: Partial<Filters>) => {
    setFilters((f) => ({ ...f, ...patch }));
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-xl font-semibold text-white">Ketersediaan Tiket</h1>
          <p className="text-sm text-slate-500">
            {data ? `${data.total} sesi aktif` : "memuat…"}
          </p>
        </div>
        <button
          onClick={() => void refresh()}
          className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm hover:bg-slate-900"
        >
          Segarkan
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <input
          value={filters.q}
          onChange={(e) => {
            update({ q: e.target.value });
            window.setTimeout(() => setDebouncedQ(e.target.value), 300);
          }}
          placeholder="Cari member…"
          className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm outline-none focus:border-pink-500"
        />
        <select
          value={filters.category}
          onChange={(e) => update({ category: e.target.value })}
          className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm outline-none"
        >
          <option value="">Semua kategori</option>
          {CATEGORY_KEYS.map((k) => (
            <option key={k} value={k}>
              {CATEGORY_LABELS[k as keyof typeof CATEGORY_LABELS]}
            </option>
          ))}
        </select>
        <select
          value={filters.status}
          onChange={(e) => update({ status: e.target.value })}
          className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm outline-none"
        >
          <option value="">Semua status</option>
          {STATUS_KEYS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-2 px-2 text-sm text-slate-400">
          <input
            type="checkbox"
            checked={filters.favoritesOnly}
            onChange={(e) => update({ favoritesOnly: e.target.checked })}
            className="accent-pink-500"
          />
          Favorit saja
        </label>
      </div>

      {error ? <p className="text-sm text-rose-300">{error}</p> : null}

      <div className="overflow-hidden rounded-xl border border-slate-800">
        <table className="w-full text-sm">
          <thead className="bg-slate-900 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Member</th>
              <th className="px-4 py-3">Kategori</th>
              <th className="px-4 py-3">Acara</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-right">Sisa tiket</th>
              <th className="px-4 py-3 text-right">Perbarui</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/70 bg-slate-900/40">
            {rows.map((row) => (
              <tr key={row.session_id} className="hover:bg-slate-900">
                <td className="px-4 py-3 font-medium text-slate-200">
                  {row.member_name ?? "–"}
                </td>
                <td className="px-4 py-3 text-slate-400">{labelCategory(row.ticket_category)}</td>
                <td className="px-4 py-3">
                  <div className="text-slate-300">{row.event_name}</div>
                  <div className="text-xs text-slate-600">
                    {row.session_label ?? `Sesi ${row.session_number ?? ""}`} ·{" "}
                    {formatDateShort(row.starts_at)}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={row.status} />
                </td>
                <td className="px-4 py-3 text-right">
                  <span className="font-medium text-slate-200">
                    {formatNumber(row.tickets_remaining)}
                  </span>
                  <span className="text-xs text-slate-600">
                    {row.total_quota ? ` / ${formatNumber(row.total_quota)}` : ""}
                  </span>
                </td>
                <td className="px-4 py-3 text-right text-xs text-slate-600">
                  {row.observed_at ? timeAgo(row.observed_at) : "–"}
                </td>
              </tr>
            ))}
            {!loading && rows.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-12 text-center text-slate-600">
                  Tidak ada data. Jalankan pemeriksaan manual atau tunggu sinkronisasi terjadwal.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}