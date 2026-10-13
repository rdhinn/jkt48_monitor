"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Dashboard", icon: "▤" },
  { href: "/availability", label: "Ketersediaan", icon: "◫" },
  { href: "/members", label: "Member", icon: "◉" },
  { href: "/schedule", label: "Jadwal", icon: "◷" },
  { href: "/history", label: "Riwayat", icon: "≣" },
  { href: "/favorites", label: "Favorit", icon: "★" },
  { href: "/settings", label: "Pengaturan", icon: "⚙" },
];

export default function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="flex h-full w-56 shrink-0 flex-col border-r border-slate-800 bg-slate-950 px-3 py-4">
      <div className="mb-6 px-2">
        <div className="text-sm font-2xl font-bold tracking-wide text-white">
          JKT48 Monitor
        </div>
        <div className="text-xs text-slate-500">ketersediaan tiket real‑time</div>
      </div>
      <nav className="flex flex-1 flex-col gap-1">
        {LINKS.map((l) => {
          const active = pathname === l.href;
          return (
            <Link
              key={l.href}
              href={l.href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                active
                  ? "bg-pink-500/15 text-pink-300"
                  : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
              }`}
            >
              <span className="w-4 text-center">{l.icon}</span>
              {l.label}
            </Link>
          );
        })}
      </nav>
      <div className="px-2 text-[11px] leading-relaxed text-slate-600">
        Data: 48pedia.id Public API
      </div>
    </aside>
  );
}