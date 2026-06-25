"use client";

import { useEffect, useState } from "react";
import { ProductNav } from "@/components/nav";
import { Card, EmptyState, Shell, StatusBadge } from "@/components/ui";
import { apiGet } from "@/lib/api";

type SetupStatus = {
  database_working: boolean;
  migrations_applied: boolean;
  stripe_configured: boolean;
  zsa_ready: boolean;
  zsa_configured: boolean;
  media_writable: boolean;
};

export default function SetupStatusPage() {
  const [status, setStatus] = useState<SetupStatus | null>(null);
  const [blocked, setBlocked] = useState(false);

  useEffect(() => {
    apiGet<SetupStatus>("/api/setup/status/")
      .then(setStatus)
      .catch(() => setBlocked(true));
  }, []);

  return (
    <Shell>
      <ProductNav />
      <header className="mb-8">
        <h1 className="text-4xl font-semibold text-white">Setup Status</h1>
        <p className="mt-2 text-white/55">Staff-only backend readiness checks. No secret values are displayed.</p>
      </header>
      {blocked ? <EmptyState title="Staff access required." detail="Sign in through Django admin to view setup status." /> : null}
      {status ? (
        <Card>
          <div className="grid gap-3 sm:grid-cols-2">
            {Object.entries(status).map(([key, value]) => (
              typeof value === "boolean" ? (
                <div key={key} className="flex items-center justify-between rounded-xl border border-white/10 bg-white/[0.04] p-4">
                  <span className="capitalize text-white/70">{key.replaceAll("_", " ")}</span>
                  <StatusBadge tone={value ? "good" : "bad"}>{value ? "OK" : "Missing"}</StatusBadge>
                </div>
              ) : null
            ))}
          </div>
        </Card>
      ) : null}
    </Shell>
  );
}
