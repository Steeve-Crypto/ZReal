"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ProductNav } from "@/components/nav";
import { Card, EmptyState, Shell, Stat, StatusBadge } from "@/components/ui";
import { ApiError, apiGet, djangoLoginUrl } from "@/lib/api";
import type { IssuerDashboard } from "@/types/api";

export default function IssuerDashboardPage() {
  const [data, setData] = useState<IssuerDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<IssuerDashboard>("/api/dashboard/issuer/")
      .then(setData)
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 403) setError("Issuer role required.");
        else setError("Sign in with an issuer account to view this dashboard.");
      });
  }, []);

  return (
    <Shell>
      <ProductNav />
      <header className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-4xl font-semibold text-white">Issuer Dashboard</h1>
          <p className="mt-2 text-white/55">Database-backed property, document, and tokenization state.</p>
        </div>
        <a className="nav-pill" href={djangoLoginUrl("/issuer/dashboard/")}>Django login</a>
      </header>
      {error ? <EmptyState title={error} detail="Choose the issuer role in Django after signing in." /> : null}
      {data ? (
        <div className="space-y-6">
          <div className="grid gap-4 md:grid-cols-4">
            <Stat label="Properties" value={data.metrics.property_count} />
            <Stat label="Tokenized" value={data.metrics.tokenized_count} />
            <Stat label="Estimated value" value={data.metrics.total_estimated_value} />
            <Stat label="ZSA issued" value={data.metrics.zsa_issued_count} />
          </div>
          <Card>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-xl font-semibold text-white">ZSA backend</h2>
                <p className="mt-1 text-sm text-white/55">{data.zsa_config.backend || "No backend configured"}</p>
              </div>
              <StatusBadge tone={data.zsa_config.ready ? "good" : "bad"}>
                {data.zsa_config.ready ? "Ready" : "ZSA backend is not configured."}
              </StatusBadge>
            </div>
            {!data.zsa_config.ready && data.zsa_config.missing.length ? (
              <ul className="mt-4 grid gap-2 text-sm text-amber-100">
                {data.zsa_config.missing.map((item) => <li key={item} className="rounded-xl border border-amber-300/20 bg-amber-300/10 px-3 py-2">{item}</li>)}
              </ul>
            ) : null}
          </Card>
          {data.properties.length ? (
            <div className="grid gap-4">
              {data.properties.map((property) => (
                <Link key={property.id} href={`/properties/${property.id}`}>
                  <Card className="transition hover:border-gold/40">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <h3 className="text-lg font-semibold text-white">{property.title}</h3>
                        <p className="mt-1 text-sm text-white/55">{property.address}</p>
                      </div>
                      <StatusBadge>{property.status_display}</StatusBadge>
                    </div>
                  </Card>
                </Link>
              ))}
            </div>
          ) : (
            <EmptyState title="No properties yet." detail="Create a property in Django or through the API to begin the issuer workflow." />
          )}
        </div>
      ) : null}
    </Shell>
  );
}
