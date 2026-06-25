import Link from "next/link";
import { Building2, Gauge, Map, ShieldCheck } from "lucide-react";

export function ProductNav() {
  return (
    <nav className="mb-10 flex flex-col gap-4 border-b border-white/10 pb-5 sm:flex-row sm:items-center sm:justify-between">
      <Link href="/" className="flex items-center gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-gold text-ink">
          <ShieldCheck size={22} />
        </span>
        <span>
          <span className="block text-xl font-semibold text-white">ZReal</span>
          <span className="text-xs uppercase tracking-[0.18em] text-gold/80">Private property rails</span>
        </span>
      </Link>
      <div className="flex flex-wrap gap-2 text-sm">
        <Link className="nav-pill" href="/issuer/dashboard"><Gauge size={16} />Issuer</Link>
        <Link className="nav-pill" href="/investor/dashboard"><Building2 size={16} />Investor</Link>
        <Link className="nav-pill" href="/properties"><Map size={16} />Browse</Link>
      </div>
    </nav>
  );
}
