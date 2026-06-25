import { clsx } from "clsx";
import type { ReactNode } from "react";

export function Shell({ children }: { children: ReactNode }) {
  return <main className="mx-auto min-h-screen w-full max-w-7xl px-5 py-6 sm:px-8 lg:px-10">{children}</main>;
}

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <section className={clsx("rounded-2xl border border-white/10 bg-white/[0.055] p-5 shadow-premium backdrop-blur", className)}>
      {children}
    </section>
  );
}

export function Stat({ label, value, detail }: { label: string; value: string | number | null; detail?: string }) {
  return (
    <Card>
      <div className="text-xs uppercase tracking-[0.18em] text-white/45">{label}</div>
      <div className="mt-3 text-3xl font-semibold text-white">{value ?? "No data yet"}</div>
      {detail ? <div className="mt-2 text-sm text-white/50">{detail}</div> : null}
    </Card>
  );
}

export function EmptyState({ title, detail }: { title: string; detail?: string }) {
  return (
    <Card className="flex min-h-44 flex-col items-center justify-center text-center">
      <div className="text-lg font-semibold text-white">{title}</div>
      {detail ? <p className="mt-2 max-w-md text-sm text-white/55">{detail}</p> : null}
    </Card>
  );
}

export function StatusBadge({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "good" | "warn" | "bad" }) {
  const classes = {
    neutral: "border-white/15 bg-white/8 text-white/70",
    good: "border-emerald-400/25 bg-emerald-400/10 text-emerald-200",
    warn: "border-amber-400/25 bg-amber-400/10 text-amber-200",
    bad: "border-red-400/25 bg-red-400/10 text-red-200"
  };
  return <span className={clsx("inline-flex rounded-full border px-3 py-1 text-xs font-medium", classes[tone])}>{children}</span>;
}
