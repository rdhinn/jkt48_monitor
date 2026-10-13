"use client";

import { useState } from "react";
import { useApi } from "@/hooks/useApi";
import { api, clearToken, getToken, login, setToken } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import type {
  MonitorRefreshResult,
  MonitorStatus,
  NotificationsOut,
  SourceStatusOut,
} from "@/types";

const EVENT_TYPES = ["all", "video_call", "meet_greet", "two_shot"];

export default function SettingsPage() {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin");
  const [chatId, setChatId] = useState("");
  const [chatIdSubmitted, setChatIdSubmitted] = useState("");
  const [eventType, setEventType] = useState("all");
  const [enabled, setEnabled] = useState(true);
  const [refreshData, setRefreshData] = useState<MonitorRefreshResult | null>(null);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const [refreshBusy, setRefreshBusy] = useState(false);

  const { data: notifs, refresh: refreshNotifs } = useApi<NotificationsOut>(
    () => api<NotificationsOut>("/notifications")
  );
  const { data: monitor, refresh: refreshMonitor } = useApi<MonitorStatus>(
    () => api<MonitorStatus>("/monitor/status")
  );
  const { data: sourcesOut } = useApi<{ sources: SourceStatusOut[] }>(
    () => api<{ sources: SourceStatusOut[] }>("/sources/status")
  );

  const isAuthed = typeof window === "undefined" ? false : getToken() !== null;

  const doLogin = async () => {
    try {
      const token = await login(username, password);
      setToken(token);
      void refreshMonitor();
    } catch (e) {
      setRefreshError(e instanceof Error ? e.message : String(e));
    }
  };

  const doRefresh = async () => {
    setRefreshBusy(true);
    setRefreshError(null);
    try {
      const result = await api<MonitorRefreshResult>("/monitor/refresh", {
        method: "POST",
        auth: true,
      });
      setRefreshData(result);
      await Promise.all([refreshNotifs(), refreshMonitor()]);
    } catch (e) {
      if (e instanceof Error) setRefreshError(e.message);
    } finally {
      setRefreshBusy(false);
    }
  };

  const saveSubscription = async () => {
    await api("/notifications", {
      method: "PUT",
      body: {
        telegram_chat_id: chatId || null,
        event_type: eventType,
        member_id: null,
        enabled,
      },
    });
    setChatIdSubmitted(chatId);
    void refreshNotifs();
  };

  const deleteSubscription = async (id: number) => {
    await api(`/notifications/${id}`, { method: "DELETE" });
    void refreshNotifs();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-white">Pengaturan</h1>
        <p className="text-sm text-slate-500">Sinkronisasi, sumber data, dan notifikasi Telegram</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <h2 className="mb-3 text-sm font-medium text-slate-400">Sinkronisasi manual</h2>
          <p className="mb-3 text-xs text-slate-500">
            Butuh autentikasi admin untuk menjalankan pemeriksaan di luar jadwal
            (dibatasi per menit).
          </p>
          {!isAuthed ? (
            <>
              <div className="mb-2 flex gap-2">
                <input
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="username"
                  className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm outline-none"
                />
                <input
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  type="password"
                  placeholder="password"
                  className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm outline-none"
                />
                <button
                  onClick={() => void doLogin()}
                  className="rounded-lg border border-slate-600 px-4 py-1.5 text-sm hover:bg-slate-800"
                >
                  Masuk
                </button>
              </div>
              <button
                onClick={() => clearToken()}
                className="text-xs text-slate-600 hover:text-slate-400"
              >
                hapus token
              </button>
            </>
          ) : (
            <div className="flex items-center gap-2">
              <button
                onClick={() => void doRefresh()}
                disabled={refreshBusy}
                className="rounded-lg bg-pink-600 px-4 py-2 text-sm font-medium text-white hover:bg-pink-500 disabled:opacity-50"
              >
                {refreshBusy ? "Menjalankan…" : "Pemeriksaan Sekarang"}
              </button>
              <button
                onClick={() => {
                  clearToken();
                  setUsername("admin");
                  setPassword("");
                }}
                className="text-xs text-slate-600 hover:text-slate-400"
              >
                keluar
              </button>
            </div>
          )}

          {refreshData ? (
            <div className="mt-3 rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-3 text-xs text-emerald-200">
              <div className="font-medium">{refreshData.message}</div>
              <div className="mt-1">
                {refreshData.members_synced} member · {refreshData.events_synced} acara ·{" "}
                {refreshData.sessions_synced} sesi · {refreshData.changes_detected} perubahan ·{" "}
                {refreshData.notifications_sent} notifikasi
              </div>
              {refreshData.errors.length ? (
                <div className="mt-1 text-rose-300">{refreshData.errors.join(" · ")}</div>
              ) : null}
            </div>
          ) : null}
          {refreshError ? (
            <div className="mt-3 rounded-lg border border-rose-500/30 bg-rose-500/5 p-3 text-xs text-rose-300">
              {refreshError}
            </div>
          ) : null}

          {monitor ? (
            <div className="mt-4 space-y-1 text-xs text-slate-500">
              <div>
                Status worker:{" "}
                <span className={monitor.running ? "text-emerald-400" : "text-slate-400"}>
                  {monitor.running ? "berjalan" : "idle"}
                </span>
              </div>
              <div>Terakhir jalan: {timeAgo(monitor.last_run_at)}</div>
              {monitor.last_error ? (
                <div className="text-rose-400">Error: {monitor.last_error}</div>
              ) : null}
            </div>
          ) : null}
        </section>

        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <h2 className="mb-3 text-sm font-medium text-slate-400">Notifikasi Telegram</h2>
          <p className="mb-3 text-xs text-slate-500">
            {notifs?.telegram_configured
              ? "Bot Telegram terpasang."
              : "Bot belum dikonfigurasi (isi TELEGRAM_BOT_TOKEN di backend)."}
          </p>
          <div className="mb-2 flex gap-2">
            <input
              value={chatId}
              onChange={(e) => setChatId(e.target.value)}
              placeholder="Telegram chat/group ID"
              className="flex-1 rounded-lg border border-slate-700 px-3 py-1.5 text-sm outline-none"
            />
            <select
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
              className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm outline-none"
            >
              {EVENT_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t === "all" ? "Semua tipe" : t}
                </option>
              ))}
            </select>
          </div>
          <div className="mb-2 flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-slate-400">
              <input
                type="checkbox"
                checked={enabled}
                onChange={(e) => setEnabled(e.target.checked)}
                className="accent-pink-500"
              />
              Aktif
            </label>
            <button
              onClick={() => void saveSubscription()}
              className="rounded-lg border border-slate-600 px-4 py-1.5 text-sm hover:bg-slate-800"
            >
              Simpan langganan
            </button>
          </div>

          <div className="space-y-2">
            {(notifs?.subscriptions ?? []).map((s) => (
              <div
                key={s.id}
                className="flex items-center justify-between rounded-lg border border-slate-800 px-3 py-2 text-sm"
              >
                <div>
                  <span className="text-slate-200">{s.telegram_chat_id ?? "chat ID belum diisi"}</span>
                  <span className="ml-2 text-xs text-slate-500">{s.event_type}</span>
                  <span className={`ml-2 text-xs ${s.enabled ? "text-emerald-400" : "text-slate-600"}`}>
                    {s.enabled ? "aktif" : "nonaktif"}
                  </span>
                </div>
                <button
                  onClick={() => void deleteSubscription(s.id)}
                  className="text-xs text-slate-600 hover:text-rose-400"
                >
                  hapus
                </button>
              </div>
            ))}
            {(notifs?.subscriptions ?? []).length === 0 ? (
              <p className="text-xs text-slate-600">
                Belum ada langganan. {chatIdSubmitted ? "" : "Isi chat ID lalu simpan."}
              </p>
            ) : null}
          </div>
        </section>
      </div>

      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <h2 className="mb-3 text-sm font-medium text-slate-400">Sumber data</h2>
        <div className="grid gap-3 md:grid-cols-3">
          {(sourcesOut?.sources ?? []).map((s) => (
            <div key={s.name} className="rounded-lg border border-slate-800 p-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-slate-200">{s.name}</span>
                {s.available ? (
                  <span className="text-xs font-medium text-emerald-400">aktif</span>
                ) : (
                  <span className="text-xs text-slate-500">nonaktif</span>
                )}
              </div>
              <p className="mt-1 text-xs text-slate-500">{s.message ?? "–"}</p>
              {s.base_url ? (
                <p className="mt-1 truncate text-[11px] text-slate-600">{s.base_url}</p>
              ) : null}
              <p className="mt-1 text-[11px] text-slate-600">
                cek terakhir: {timeAgo(s.last_checked_at)}
              </p>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <h2 className="mb-3 text-sm font-medium text-slate-400">Riwayat notifikasi</h2>
        {(notifs?.logs ?? []).length ? (
          <div className="space-y-1.5">
            {notifs!.logs.slice(0, 15).map((log) => (
              <div key={log.id} className="flex items-center gap-2 text-xs">
                <span className="w-40 shrink-0 truncate text-slate-500">
                  {timeAgo(log.attempted_at)}
                </span>
                <span
                  className={`font-medium ${
                    log.delivery_status === "sent"
                      ? "text-emerald-400"
                      : log.delivery_status === "failed"
                        ? "text-rose-400"
                        : "text-slate-400"
                  }`}
                >
                  {log.delivery_status}
                </span>
                <span className="truncate text-slate-400">{log.message}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-slate-600">Belum ada log.</p>
        )}
      </section>
    </div>
  );
}