import Link from "next/link";
import { ArrowRight, FileText, LockKeyhole, ShieldCheck } from "lucide-react";
import { ProductNav } from "@/components/nav";
import { Card, Shell } from "@/components/ui";

export default function HomePage() {
  return (
    <Shell>
      <ProductNav />
      <section className="grid gap-8 py-10 lg:grid-cols-[1.15fr_0.85fr] lg:items-center">
        <div>
          <div className="mb-4 text-xs uppercase tracking-[0.22em] text-gold">Private property rails</div>
          <h1 className="max-w-4xl text-5xl font-semibold leading-[0.95] text-white sm:text-7xl">
            Private real estate tokenization with issuer-controlled workflows.
          </h1>
          <p className="mt-6 max-w-2xl text-lg text-white/62">
            ZReal helps issuers organize property records, review supporting documents, and manage ZSA tokenization readiness from one secure workspace.
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
              <h2 className="font-semibold text-white">Verified issuance history</h2>
              <p className="mt-1 text-sm text-white/58">Tokenization records reflect submitted operations and identifiers returned by approved issuance tooling.</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <FileText className="mt-1 text-mint" />
            <div>
              <h2 className="font-semibold text-white">Issuer review first</h2>
              <p className="mt-1 text-sm text-white/58">Autofilled property details and uploaded documents remain reviewable before they support readiness.</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <LockKeyhole className="mt-1 text-white/70" />
            <div>
              <h2 className="font-semibold text-white">Secure account access</h2>
              <p className="mt-1 text-sm text-white/58">Role-based access keeps issuer, investor, and staff workflows separated.</p>
            </div>
          </div>
        </Card>
      </section>
    </Shell>
  );
}
