"use client";

import { useMemo } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import StatusBadge from "@/components/StatusBadge";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { formatDate, formatNumber } from "@/lib/format";
import type { HistoryPoint, Page } from "@/types";

export default function HistoryPage() {
  const { data, loading, error } = useApi<Page<HistoryPoint>>(
    () =>
      api<Page<HistoryPoint>>(
        "/availability/history?per_page=500"
      ),
    null
  );

  const points = useMemo(() => data?.items ?? [], [data]);

  const chartData = useMemo(() => {
    const byDate = new Map<string, { remainingSum: number; count: number; label: string }>();
    for (const p of points) {
      if (p.tickets_remaining === null || p.tickets_remaining === undefined) continue;
      const d = new Date(p.observed_at);
      if (Number.isNaN(d.getTime())) continue;
      const key = d.toISOString().replace(/T.*/, "");
      const entry = byDate.get(key) ?? { remainingSum: 0, count: 0, label: key };
      entry.remainingSum += p.tickets_remaining;
      entry.count += 1;
      byDate.set(key, entry);
    }
    return [...byDate.entries()]
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([key, v]) => ({
        date: key,
        average: Math.round((v.remainingSum / v.count) * 10) / 10,
        count: v.count,
      }));
  }, [points]);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-white">Riwayat Ketersediaan</h1>
        <p className="text-sm text-slate-500">
          {data ? `${data.total} titik data snapshot` : "memuat…"}
        </p>
      </div>

      {error ? <p className="text-sm text-rose-300">{error}</p> : null}

      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <h2 className="mb-2 text-sm font-medium text-slate-400">
          Rata-rata sisa tiket per hari
        </h2>
        {chartData.length ? (
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={chartData} margin={{ left: -20 }}>
              <defs>
                <linearGradient id="tickets" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ec4899" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#ec4899" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="date" tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} allowDecimals />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#0f172a",
                  border: "1px solid #334155",
                  borderRadius: 8,
                  color: "#e2e8f0",
                }}
              />
              <Area
                type="monotone"
                dataKey="average"
                stroke="#ec4899"
                strokeWidth={2}
                fill="url(#tickets)"
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <p className="py-12 text-center text-sm text-slate-600">Belum ada data riwayat.</p>
        )}
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-800">
        <table className="w-full text-sm">
          <thead className="bg-slate-900 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Waktu</th>
              <th className="px-4 py-3">Member</th>
              <th className="px-4 py-3">Acara</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-right">Sisa</th>
              <th className="px-4 py-3 text-right">Terjual</th>
              <th className="px-4 py-3">Sumber</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/70 bg-slate-900/40">
            {points.map((p, i) => (
              <tr key={`${p.session_id}-${p.observed_at}-${i}`} className="hover:bg-slate-900">
                <td className="px-4 py-2.5 text-xs text-slate-400">{formatDate(p.observed_at)}</td>
                <td className="px-4 py-2.5 font-medium text-slate-200">{p.member_name ?? "–"}</td>
                <td className="px-4 py-2.5 text-slate-400">{p.event_name}</td>
                <td className="px-4 py-2.5">
                  <StatusBadge status={p.status} />
                </td>
                <td className="px-4 py-2.5 text-right text-slate-300">
                  {formatNumber(p.tickets_remaining)}
                </td>
                <td className="px-4 py-2.5 text-right text-slate-400">{formatNumber(p.sold_count)}</td>
                <td className="px-4 py-2.5 text-xs text-slate-600">{p.source}</td>
              </tr>
            ))}
            {!loading && points.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-12 text-center text-slate-600">
                  Belum ada snapshot tersimpan.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}