import { ReactNode } from "react";

export default function StatCard({ label, value, icon, tone = "bg-white" }: { label: string; value: string; icon: ReactNode; tone?: string }) {
  return (
    <div className={`rounded-3xl ${tone} p-5 shadow-soft`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-slate-500">{label}</p>
          <p className="mt-3 text-3xl font-semibold text-ink">{value}</p>
        </div>
        <div className="rounded-2xl bg-ink/5 p-3 text-tide">{icon}</div>
      </div>
    </div>
  );
}
