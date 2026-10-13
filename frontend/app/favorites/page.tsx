"use client";

import { useMemo } from "react";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import type { MemberOut } from "@/types";

export default function FavoritesPage() {
  const { data, loading, refresh } = useApi<MemberOut[]>(
    () => api<MemberOut[]>("/favorites")
  );

  const members = useMemo(() => data ?? [], [data]);

  const remove = async (m: MemberOut) => {
    await api(`/favorites/${m.id}`, { method: "DELETE" });
    void refresh();
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-white">Member Favorit</h1>
        <p className="text-sm text-slate-500">{members.length} favorit</p>
      </div>

      {members.length ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {members.map((m) => (
            <div
              key={m.id}
              className="flex items-center gap-4 rounded-xl border border-slate-800 bg-slate-900/60 p-4"
            >
              {m.image_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={m.image_url}
                  alt={m.name}
                  className="h-14 w-14 rounded-full object-cover"
                />
              ) : (
                <div className="flex h-14 w-14 items-center justify-center rounded-full bg-slate-800 text-xl text-slate-500">
                  {m.name.charAt(0)}
                </div>
              )}
              <div className="min-w-0 flex-1">
                <div className="truncate font-medium text-slate-200">{m.name}</div>
                <div className="text-xs text-slate-500">
                  {[m.team_code, m.generation_code].filter(Boolean).join(" · ") || "–"}
                </div>
              </div>
              <button
                onClick={() => void remove(m)}
                className="text-lg leading-none text-pink-400 hover:text-pink-300"
                title="Hapus dari favorit"
              >
                ★
              </button>
            </div>
          ))}
        </div>
      ) : (
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-12 text-center text-slate-600">
          {loading ? "Memuat…" : "Belum ada favorit. Tambahkan dari halaman Member."}
        </div>
      )}
    </div>
  );
}