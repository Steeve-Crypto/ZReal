"use client";

import { use, useEffect, useState } from "react";
import { ProductNav } from "@/components/nav";
import { Card, EmptyState, Shell, StatusBadge } from "@/components/ui";
import { ApiError, apiGet, apiJson } from "@/lib/api";
import type { TokenizationOperation } from "@/types/api";

export default function TokenizationOperationPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [operation, setOperation] = useState<TokenizationOperation | null>(null);
  const [error, setError] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  async function loadOperation() {
    const record = await apiGet<TokenizationOperation>(`/api/tokenization/operations/${id}/`);
    setOperation(record);
  }

  useEffect(() => {
    loadOperation().catch(() => setError(true));
  }, [id]);

  async function refreshStatus() {
    setRefreshing(true);
    setActionError(null);
    try {
      const updated = await apiJson<TokenizationOperation>(`/api/tokenization/operations/${id}/refresh/`, "POST", {});
      setOperation(updated);
    } catch (err) {
      if (err instanceof ApiError && err.data) setActionError(JSON.stringify(err.data));
      else setActionError(err instanceof Error ? err.message : "Could not refresh tokenization status.");
      await loadOperation().catch(() => undefined);
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <Shell>
      <ProductNav />
      {error ? <EmptyState title="Tokenization operation not available." detail="Only the issuer owner or staff can view operation details." /> : null}
      {operation ? (
        <div className="space-y-6">
          <header className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h1 className="text-4xl font-semibold text-white">{operation.property.title}</h1>
              <p className="mt-2 text-white/55">{operation.asset_symbol}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {operation.can_refresh ? (
                <button disabled={refreshing} onClick={() => void refreshStatus()} className="rounded-full border border-white/15 bg-white/[0.06] px-4 py-2 text-sm font-medium text-white transition hover:border-gold/50 disabled:opacity-50">
                  {refreshing ? "Refreshing..." : "Refresh status"}
                </button>
              ) : null}
              <StatusBadge tone={operation.status === "confirmed" ? "good" : operation.status === "failed" ? "bad" : "warn"}>{operation.status}</StatusBadge>
            </div>
          </header>
          {actionError ? <div className="rounded-xl border border-red-400/25 bg-red-400/10 px-4 py-3 text-sm text-red-100">{actionError}</div> : null}
          <Card>
            <dl className="grid gap-4 text-sm sm:grid-cols-2">
              <div><dt className="text-white/40">Backend</dt><dd>{operation.backend}</dd></div>
              <div><dt className="text-white/40">Issuer address</dt><dd>{operation.issuer_zaddr_masked ?? "No data yet"}</dd></div>
              <div><dt className="text-white/40">Operation ID</dt><dd className="break-all">{operation.operation_id ?? "No data yet"}</dd></div>
              <div><dt className="text-white/40">Txid</dt><dd className="break-all">{operation.txid ?? "No data yet"}</dd></div>
              <div><dt className="text-white/40">Asset ID</dt><dd className="break-all">{operation.asset_id ?? "No data yet"}</dd></div>
              <div><dt className="text-white/40">Error</dt><dd>{operation.error ?? "No error recorded"}</dd></div>
              <div><dt className="text-white/40">Created</dt><dd>{operation.created_at ?? "No data yet"}</dd></div>
              <div><dt className="text-white/40">Broadcast</dt><dd>{operation.broadcast_at ?? "No data yet"}</dd></div>
              <div><dt className="text-white/40">Confirmed</dt><dd>{operation.confirmed_at ?? "No data yet"}</dd></div>
              <div><dt className="text-white/40">Failed</dt><dd>{operation.failed_at ?? "No data yet"}</dd></div>
              <div><dt className="text-white/40">Last refresh</dt><dd>{operation.last_status_refreshed_at ?? "No data yet"}</dd></div>
            </dl>
          </Card>
          <Card>
            <h2 className="text-xl font-semibold text-white">Safe metadata</h2>
            <pre className="mt-4 overflow-auto rounded-xl bg-black/25 p-4 text-xs text-white/65">{JSON.stringify(operation.safe_metadata, null, 2)}</pre>
          </Card>
          {operation.can_view_raw_response ? (
            <Card>
              <h2 className="text-xl font-semibold text-white">Raw backend response</h2>
              <pre className="mt-4 overflow-auto rounded-xl bg-black/25 p-4 text-xs text-white/65">{JSON.stringify(operation.raw_response ?? {}, null, 2)}</pre>
            </Card>
          ) : null}
        </div>
      ) : null}
    </Shell>
  );
}
