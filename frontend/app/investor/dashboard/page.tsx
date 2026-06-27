"use client";

import { useEffect, useState } from "react";
import { ProductNav } from "@/components/nav";
import { EmptyState, Shell, Stat } from "@/components/ui";
import { ApiError, apiGet, djangoLoginUrl } from "@/lib/api";
import type { InvestorDashboard } from "@/types/api";

export default function InvestorDashboardPage() {
  const [data, setData] = useState<InvestorDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<InvestorDashboard>("/api/dashboard/investor/")
      .then(setData)
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 403) setError("Investor access is required.");
        else setError("Sign in with an investor account to view this dashboard.");
      });
  }, []);

  return (
    <Shell>
      <ProductNav />
      <header className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-4xl font-semibold text-white">Investor Dashboard</h1>
          <p className="mt-2 text-white/55">Review your tokenized property positions and available opportunities.</p>
        </div>
        <a className="nav-pill" href={djangoLoginUrl("/investor/dashboard/")}>Sign in</a>
      </header>
      {error ? <EmptyState title={error} detail="Sign in and select investor access from your account settings." /> : null}
      {data ? (
        <div className="space-y-6">
          <div className="grid gap-4 md:grid-cols-3">
            <Stat label="Portfolio value" value={data.metrics.total_portfolio_value} />
            <Stat label="Holdings" value={data.metrics.investment_count} />
            <Stat label="Available properties" value={data.metrics.available_property_count} />
          </div>
          {data.holdings.length ? (
            <div className="grid gap-4">
              {data.holdings.map((holding) => <Stat key={holding.id} label={holding.property.title} value={holding.estimated_position_value} detail={`${holding.shares_owned} shares`} />)}
            </div>
          ) : (
            <EmptyState title="No holdings yet." detail="Tokenized property positions will appear here after purchase." />
          )}
        </div>
      ) : null}
    </Shell>
  );
}
