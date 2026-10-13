"use client";

import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import StatCard from "@/components/StatCard";
import StatusBadge from "@/components/StatusBadge";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import {
  CATEGORY_COLORS,
  fieldLabel,
  formatDate,
  labelCategory,
  labelStatus,
  timeAgo,
} from "@/lib/format";
import type { DashboardOut } from "@/types";

export default function DashboardPage() {
  const { data, loading, error, refresh } = useApi<DashboardOut>(
    () => api<DashboardOut>("/dashboard"),
    30000
  );

  const categoryData = useMemo(() => {
    if (!data) return [];
    const colors = Object.keys(data.availability_by_category);
    return Object.entries(data.availability_by_category)
      .sort((a, b) => b[1] - a[1])
      .map(([key, value], i) => ({
        name: labelCategory(key),
        value,
        color: CATEGORY_COLORS[i % CATEGORY_COLORS.length] ?? "#64748b",
        _index: colors.length ? colors.indexOf(key) : i,
      }));
  }, [data]);

  if (loading && !data) {
    return <div className="py-20 text-center text-slate-500">Memuat dashboard…</div>;
  }

  if (error && !data) {
    return (
      <div className="py-20 text-center">
        <p className="text-rose-300">{error}</p>
        <p className="mt-2 text-sm text-slate-500">
          Pastikan backend berjalan di <code>http://localhost:8000</code>
        </p>
        <button
          onClick={() => void refresh()}
          className="mt-4 rounded-lg border border-slate-700 px-4 py-2 text-sm hover:bg-slate-900"
        >
          Coba lagi
        </button>
      </div>
    );
  }

  const stats = data?.stats;
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-xl font-semibold text-white">Dashboard</h1>
          <p className="text-sm text-slate-500">
            Terakhir diperbarui {stats?.last_observed_at ? timeAgo(stats.last_observed_at) : "–"}
          </p>
        </div>
        <button
          onClick={() => void refresh()}
          className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm hover:bg-slate-900"
        >
          Segarkan
        </button>
      </div>

      {stats?.notes && stats.notes.length > 0 && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 text-sm text-amber-200">
          {stats.notes.map((n) => (
            <div key={n}>{n}</div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Member" value={stats?.total_members ?? 0} hint={`${stats?.active_members ?? 0} aktif`} />
        <StatCard label="Sesi ketersediaan" value={stats?.total_sessions ?? 0} />
        <StatCard
          label="Tersedia"
          value={stats?.available_sessions ?? 0}
          tone={stats?.available_sessions ? "success" : "default"}
        />
        <StatCard
          label="Habis"
          value={stats?.sold_out_sessions ?? 0}
          tone={stats?.sold_out_sessions ? "danger" : "default"}
        />
        <StatCard label="Belum dibuka" value={stats?.not_open_sessions ?? 0} tone="warn" />
        <StatCard label="Penurunan stok" value={stats?.sessions_with_declining_stock ?? 0} tone="warn" />
        <StatCard label="Sesi per kategori" value="→" />
        <StatCard
          label="API 48pedia"
          value={stats?.api_connected ? "Terhubung" : "Belum"}
          tone={stats?.api_connected ? "success" : "dim"}
          hint={stats?.api_connected ? "sukses" : "konfigurasi JKT48_API_KEY"}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 lg:col-span-2">
          <h2 className="mb-2 text-sm font-medium text-slate-400">Stok per kategori</h2>
          {categoryData.length ? (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={categoryData} margin={{ left: -20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 12 }} />
                <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} allowDecimals={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0f172a",
                    border: "1px solid #334155",
                    borderRadius: 8,
                    color: "#e2e8f0",
                  }}
                />
                <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                  {categoryData.map((entry) => (
                    <Cell key={entry.name} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="py-16 text-center text-sm text-slate-600">
              Belum ada data ketersediaan.
            </div>
          )}
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <h2 className="mb-2 text-sm font-medium text-slate-400">Sumber data</h2>
          <div className="space-y-3">
            {data?.sources.map((s) => (
              <div key={s.name} className="rounded-lg border border-slate-800 p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-200">{s.name}</span>
                  {s.available ? (
                    <span className="text-xs font-medium text-emerald-400">aktif</span>
                  ) : (
                    <span className="text-xs font-medium text-slate-500">
                      {s.configured ? "error" : "belum dikonfigurasi"}
                    </span>
                  )}
                </div>
                <p className="mt-1 text-xs text-slate-500">{s.message ?? "–"}</p>
                {s.last_error ? <p className="mt-1 text-xs text-rose-400">{s.last_error}</p> : null}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <h2 className="mb-3 text-sm font-medium text-slate-400">Perubahan terbaru</h2>
        {data?.recent_changes.length ? (
          <div className="space-y-2">
            {data.recent_changes.map((c, i) => (
              <div key={`${c.session_id}-${c.observed_at}-${i}`} className="flex items-center gap-3 text-sm">
                <span className="w-32 shrink-0 truncate text-slate-300">
                  {c.member_name ?? c.event_name}
                </span>
                <span className="w-24 shrink-0 text-xs text-slate-500">{labelCategory(c.ticket_category)}</span>
                <StatusBadge status={c.current ?? c.previous ?? "unknown"} />
                <span className="text-xs text-slate-600">{fieldLabel(c.field)}</span>
                <span className="ml-auto shrink-0 text-xs text-slate-600" title={formatDate(c.observed_at)}>
                  {timeAgo(c.observed_at)}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-600">Belum ada perubahan tercatat.</p>
        )}
      </div>
    </div>
  );
}