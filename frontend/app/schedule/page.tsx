"use client";

import { useMemo, useState } from "react";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { formatDateShort, labelCategory } from "@/lib/format";
import type { EventOut, Page } from "@/types";

const ENTRY_TYPES = ["", "SHOW", "EVENT", "EXCLUSIVE", "BIRTHDAY", "GENERAL"];

export default function SchedulePage() {
  const [entryType, setEntryType] = useState("");

  const buildQuery = () => {
    const params = new URLSearchParams({ per_page: "200" });
    if (entryType) params.set("entry_type", entryType);
    return params.toString() ? `?${params.toString()}` : "";
  };

  const { data, loading, refresh } = useApi<Page<EventOut>>(
    () => api<Page<EventOut>>(`/events${buildQuery()}`),
    null
  );

  const events = useMemo(() => data?.items ?? [], [data]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-xl font-semibold text-white">Jadwal &amp; Acara</h1>
          <p className="text-sm text-slate-500">{data ? `${data.total} acara` : "memuat…"}</p>
        </div>
        <button
          onClick={() => void refresh()}
          className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm hover:bg-slate-900"
        >
          Segarkan
        </button>
      </div>

      <div className="flex items-center gap-2">
        <select
          value={entryType}
          onChange={(e) => setEntryType(e.target.value)}
          className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm outline-none"
        >
          {ENTRY_TYPES.map((t) => (
            <option key={t} value={t}>
              {t === "" ? "Semua tipe" : t}
            </option>
          ))}
        </select>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-800">
        <table className="w-full text-sm">
          <thead className="bg-slate-900 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Acara</th>
              <th className="px-4 py-3">Tipe</th>
              <th className="px-4 py-3">Kategori</th>
              <th className="px-4 py-3">Sesi</th>
              <th className="px-4 py-3">Mulai</th>
              <th className="px-4 py-3">Aktif</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/70 bg-slate-900/40">
            {events.map((e) => (
              <tr key={e.id} className="hover:bg-slate-900">
                <td className="px-4 py-3 font-medium text-slate-200">{e.name}</td>
                <td className="px-4 py-3 text-slate-400">{e.entry_type}</td>
                <td className="px-4 py-3 text-slate-400">
                  {e.category ? labelCategory(e.category) : "–"}
                </td>
                <td className="px-4 py-3 text-slate-400">{e.sessions.length}</td>
                <td className="px-4 py-3 text-slate-400">{formatDateShort(e.starts_at)}</td>
                <td className="px-4 py-3">
                  {e.is_active ? (
                    <span className="text-xs font-medium text-emerald-400">aktif</span>
                  ) : (
                    <span className="text-xs text-slate-600">nonaktif</span>
                  )}
                </td>
              </tr>
            ))}
            {!loading && events.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-12 text-center text-slate-600">
                  Belum ada data jadwal.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}