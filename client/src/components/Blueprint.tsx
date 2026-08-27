import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

export function PageHeader({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: React.ReactNode }) {
  return (
    <header className="relative overflow-hidden border-b border-slate-700 pb-6 sm:flex sm:items-end sm:justify-between">
      <div className="absolute bottom-0 left-0 h-px w-28 bg-sky-400" />
      <div className="max-w-3xl">
        <p className="section-kicker">{eyebrow}</p>
        <h1 className="mt-2 font-display text-2xl font-semibold tracking-tight text-white sm:text-3xl">{title}</h1>
        <p className="mt-2 text-sm leading-6 text-slate-400">{description}</p>
      </div>
      {action ? <div className="mt-5 shrink-0 sm:mt-0">{action}</div> : null}
    </header>
  );
}

export function TechCard({ children, className, label }: { children: React.ReactNode; className?: string; label?: string }) {
  return (
    <section className={cn("tech-card relative", className)}>
      {label ? <span className="absolute -top-2 left-4 rounded bg-[#1e293b] px-2 font-mono text-[10px] tracking-[0.14em] text-sky-400">{label}</span> : null}
      {children}
    </section>
  );
}

export function StatusPill({ status, className }: { status: string; className?: string }) {
  const tone = status.includes("healthy") || status.includes("connected") || status.includes("online") || status.includes("succeeded") || status.includes("delivered")
    ? "border-emerald-300/35 bg-emerald-300/10 text-emerald-200"
    : status.includes("critical") || status.includes("failed") || status.includes("disconnected")
      ? "border-rose-300/35 bg-rose-300/10 text-rose-100"
      : status.includes("warning") || status.includes("high") || status.includes("approval") || status.includes("degraded")
        ? "border-amber-200/35 bg-amber-200/10 text-amber-100"
        : "border-blue-200/25 bg-blue-200/8 text-blue-100/75";
  return <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.08em]", tone, className)}><span className="h-1.5 w-1.5 rounded-full bg-current" />{status.replaceAll("_", " ")}</span>;
}

export function MetricCard({ label, value, detail, icon: Icon, accent = "cyan" }: { label: string; value: number | string; detail: string; icon: LucideIcon; accent?: "cyan" | "amber" | "rose" | "blue" }) {
  const accentClasses = { cyan: "text-cyan-200 border-cyan-200/30", amber: "text-amber-100 border-amber-100/30", rose: "text-rose-100 border-rose-100/30", blue: "text-blue-100 border-blue-100/30" };
  return (
    <TechCard>
      <div className="flex items-start justify-between gap-3">
        <p className="font-mono text-[10px] uppercase tracking-[0.15em] text-blue-200/60">{label}</p>
        <span className={cn("grid h-8 w-8 place-items-center border", accentClasses[accent])}><Icon className="h-4 w-4" /></span>
      </div>
      <p className="mt-5 font-display text-3xl font-semibold tabular-nums text-white">{value}</p>
      <p className="mt-2 text-xs leading-5 text-blue-100/60">{detail}</p>
    </TechCard>
  );
}
