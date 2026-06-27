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
          <p className="mt-2 text-white/55">Track property drafts, document readiness, and tokenization operations.</p>
        </div>
        <a className="nav-pill" href={djangoLoginUrl("/issuer/dashboard/")}>Sign in</a>
      </header>
      {error ? <EmptyState title={error} detail="Sign in and choose issuer access from your account settings." /> : null}
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
                <h2 className="text-xl font-semibold text-white">Tokenization Setup</h2>
                <p className="mt-1 text-sm text-white/55">{data.zsa_config.ready ? "Issuance configuration is complete." : "Configuration incomplete"}</p>
              </div>
              <StatusBadge tone={data.zsa_config.ready ? "good" : "bad"}>
                {data.zsa_config.ready ? "Ready" : "Setup required"}
              </StatusBadge>
            </div>
            {!data.zsa_config.ready && data.zsa_config.missing.length ? (
              <ul className="mt-4 grid gap-2 text-sm text-amber-100">
                {data.zsa_config.missing.map((item) => <li key={item} className="rounded-xl border border-amber-300/20 bg-amber-300/10 px-3 py-2">{item}</li>)}
              </ul>
            ) : null}
          </Card>
          <div className="grid gap-4 lg:grid-cols-2">
            <ActionGroup title="Needs Documents" properties={data.action_groups.needs_documents} empty="No draft properties waiting on documents." />
            <ActionGroup title="Ready For Tokenization" properties={data.action_groups.ready_for_tokenization} empty="No properties are ready for tokenization yet." />
            <ActionGroup title="Waiting For Confirmation" properties={data.action_groups.waiting_for_confirmation} empty="No pending tokenization operations." />
            <ActionGroup title="Failed Tokenization" properties={data.action_groups.failed_tokenization} empty="No failed tokenization operations." tone="bad" />
          </div>
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
            <EmptyState title="No properties yet." detail="Create your first property draft to begin the issuer workflow." />
          )}
        </div>
      ) : null}
    </Shell>
  );
}

function ActionGroup({
  title,
  properties,
  empty,
  tone = "neutral"
}: {
  title: string;
  properties: IssuerDashboard["properties"];
  empty: string;
  tone?: "neutral" | "bad";
}) {
  return (
    <Card>
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-white">{title}</h2>
        <StatusBadge tone={tone === "bad" && properties.length ? "bad" : "neutral"}>{properties.length}</StatusBadge>
      </div>
      {properties.length ? (
        <div className="mt-4 grid gap-3">
          {properties.slice(0, 4).map((property) => (
            <Link key={property.id} href={`/properties/${property.id}`} className="rounded-xl border border-white/10 bg-white/[0.04] p-4 transition hover:border-gold/40">
              <div className="font-medium text-white">{property.title}</div>
              <div className="mt-1 text-sm text-white/50">{property.readiness.next_action.replaceAll("_", " ")}</div>
            </Link>
          ))}
        </div>
      ) : (
        <p className="mt-4 text-sm text-white/50">{empty}</p>
      )}
    </Card>
  );
}
