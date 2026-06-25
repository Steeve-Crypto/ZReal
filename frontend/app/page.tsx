import Link from "next/link";
import { ArrowRight, Database, LockKeyhole, ShieldCheck } from "lucide-react";
import { ProductNav } from "@/components/nav";
import { Card, Shell } from "@/components/ui";

export default function HomePage() {
  return (
    <Shell>
      <ProductNav />
      <section className="grid gap-8 py-10 lg:grid-cols-[1.15fr_0.85fr] lg:items-center">
        <div>
          <div className="mb-4 text-xs uppercase tracking-[0.22em] text-gold">Django backend. Next product UI.</div>
          <h1 className="max-w-4xl text-5xl font-semibold leading-[0.95] text-white sm:text-7xl">
            Private real estate tokenization without pretend data.
          </h1>
          <p className="mt-6 max-w-2xl text-lg text-white/62">
            ZReal connects issuer property workflows, document processing, and real ZSA tokenization status through a dedicated product frontend backed by Django APIs.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/issuer/dashboard" className="nav-pill bg-gold text-ink hover:text-ink">
              Issuer dashboard <ArrowRight size={16} />
            </Link>
            <Link href="/properties" className="nav-pill">
              Browse properties
            </Link>
          </div>
        </div>
        <Card className="space-y-5">
          <div className="flex items-start gap-4">
            <ShieldCheck className="mt-1 text-gold" />
            <div>
              <h2 className="font-semibold text-white">Truthful tokenization</h2>
              <p className="mt-1 text-sm text-white/58">No fake txids, asset IDs, yields, activity feeds, holdings, or deed content.</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <Database className="mt-1 text-mint" />
            <div>
              <h2 className="font-semibold text-white">Django remains source of truth</h2>
              <p className="mt-1 text-sm text-white/58">Admin, auth, documents, properties, and ZSA integration stay in the backend.</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <LockKeyhole className="mt-1 text-white/70" />
            <div>
              <h2 className="font-semibold text-white">Session-based local auth</h2>
              <p className="mt-1 text-sm text-white/58">Use Django login locally; the frontend sends credentials to the configured API origin.</p>
            </div>
          </div>
        </Card>
      </section>
    </Shell>
  );
}
