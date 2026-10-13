import type { Metadata } from "next";
import Sidebar from "@/components/Sidebar";
import "./globals.css";

export const metadata: Metadata = {
  title: "JKT48 Monitor",
  description: "Monitoring ketersediaan tiket JKT48 dari 48pedia.id",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id">
      <body>
        <div className="flex h-screen overflow-hidden">
          <Sidebar />
          <main className="flex-1 overflow-y-auto">
            <div className="mx-auto max-w-6xl px-6 py-6">{children}</div>
          </main>
        </div>
      </body>
    </html>
  );
}