"use client";

import { useMemo, useState } from "react";
import StatusBadge from "@/components/StatusBadge";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { CATEGORY_LABELS, formatNumber } from "@/lib/format";
import type { MemberOut, Page } from "@/types";

export default function MembersPage() {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [favoritesOnly, setFavoritesOnly] = useState(false);
  const [category, setCategory] = useState("");

  const buildQuery = () => {
    const params = new URLSearchParams({ per_page: "200", active_only: "true" });
    if (q) params.set("q", q);
    if (status) params.set("status", status);
    if (category) params.set("category", category);
    if (favoritesOnly) params.set("favorites_only", "true");
    const qs = params.toString();
    return qs ? `?${qs}` : "";
  };

  const { data, refresh } = useApi<Page<MemberOut>>(
    () => api<Page<MemberOut>>(`/members${buildQuery()}`),
    null
  );

  const members = useMemo(() => data?.items ?? [], [data]);

  const toggleFavorite = async (m: MemberOut) => {
    if (m.is_favorite) {
      await api(`/favorites/${m.id}`, { method: "DELETE" });
    } else {
      await api(`/favorites/${m.id}`, { method: "POST" });
    }
    void refresh();
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-xl font-semibold text-white">Member</h1>
          <p className="text-sm text-slate-500">{data ? `${data.total} member` : "memuat…"}</p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Cari nama…"
          className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm outline-none focus:border-pink-500"
        />
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm outline-none"
        >
          <option value="">Semua status</option>
          <option value="available">available</option>
          <option value="sold_out">sold_out</option>
        </select>
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm outline-none"
        >
          <option value="">Semua kategori</option>
          {Object.entries(CATEGORY_LABELS).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-2 px-2 text-sm text-slate-400">
          <input
            type="checkbox"
            checked={favoritesOnly}
            onChange={(e) => setFavoritesOnly(e.target.checked)}
            className="accent-pink-500"
          />
          Favorit saja
        </label>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-800">
        <table className="w-full text-sm">
          <thead className="bg-slate-900 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3"></th>
              <th className="px-4 py-3">Nama</th>
              <th className="px-4 py-3">Tim</th>
              <th className="px-4 py-3">Generasi</th>
              <th className="px-4 py-3 text-right">Sisa tiket</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/70 bg-slate-900/40">
            {members.map((m) => (
              <tr key={m.id} className="hover:bg-slate-900">
                <td className="px-4 py-3">
                  <button
                    onClick={() => void toggleFavorite(m)}
                    title={m.is_favorite ? "Hapus dari favorit" : "Tambah ke favorit"}
                    className={`text-lg leading-none ${m.is_favorite ? "text-pink-400" : "text-slate-700 hover:text-slate-400"}`}
                  >
                    ★
                  </button>
                </td>
                <td className="px-4 py-3">
                  <div className="font-medium text-slate-200">{m.name}</div>
                  {m.nickname && m.nickname !== m.name ? (
                    <div className="text-xs text-slate-500">{m.nickname}</div>
                  ) : null}
                </td>
                <td className="px-4 py-3 text-slate-400">{m.team_code ?? "–"}</td>
                <td className="px-4 py-3 text-slate-400">{m.generation_code ?? "–"}</td>
                <td className="px-4 py-3 text-right text-slate-300">
                  {m.is_favorite ? "–" : formatNumber(null)}
                </td>
                <td className="px-4 py-3">
                  {m.is_favorite ? (
                    <StatusBadge status="unknown" />
                  ) : (
                    <span className="text-xs text-slate-600">lihat detail acara</span>
                  )}
                </td>
              </tr>
            ))}
            {members.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-12 text-center text-slate-600">
                  Belum ada data member. Jalankan sinkronisasi terlebih dahulu.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}