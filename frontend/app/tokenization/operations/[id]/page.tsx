"use client";

import { use, useEffect, useState } from "react";
import { ProductNav } from "@/components/nav";
import { Card, EmptyState, Shell, StatusBadge } from "@/components/ui";
import { apiGet, apiJson, userFacingError } from "@/lib/api";
import type { TokenizationMutationResponse, TokenizationOperation } from "@/types/api";

function labelFromKey(key: string) {
  return key.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function metadataEntries(metadata: Record<string, unknown>) {
  return Object.entries(metadata).filter(([, value]) => value !== null && value !== undefined && value !== "");
}

export default function TokenizationOperationPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [operation, setOperation] = useState<TokenizationOperation | null>(null);
  const [error, setError] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
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
    setActionMessage(null);
    try {
      const response = await apiJson<TokenizationMutationResponse>(`/api/tokenization/operations/${id}/refresh/`, "POST", {});
      setOperation(response.operation);
      setActionMessage(response.notifications.map((item) => item.message).join(" "));
    } catch (err) {
      setActionError(userFacingError(err, "Could not refresh tokenization status."));
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
          {actionMessage ? <div className="rounded-xl border border-emerald-400/25 bg-emerald-400/10 px-4 py-3 text-sm text-emerald-100">{actionMessage}</div> : null}
          <Card>
            <dl className="grid gap-4 text-sm sm:grid-cols-2">
              <div><dt className="text-white/40">Issuance method</dt><dd>{operation.backend ? "Configured issuer tooling" : "No data yet"}</dd></div>
              <div><dt className="text-white/40">Issuer address</dt><dd>{operation.issuer_zaddr_masked ?? "No data yet"}</dd></div>
              <div><dt className="text-white/40">Operation ID</dt><dd className="break-all">{operation.operation_id ?? "No data yet"}</dd></div>
              <div><dt className="text-white/40">Transaction ID</dt><dd className="break-all">{operation.txid ?? "No data yet"}</dd></div>
              <div><dt className="text-white/40">Asset ID</dt><dd className="break-all">{operation.asset_id ?? "No data yet"}</dd></div>
              <div><dt className="text-white/40">Error</dt><dd>{operation.error ?? "No error recorded"}</dd></div>
              <div><dt className="text-white/40">Created</dt><dd>{operation.created_at ?? "No data yet"}</dd></div>
              <div><dt className="text-white/40">Broadcast</dt><dd>{operation.broadcast_at ?? "No data yet"}</dd></div>
              <div><dt className="text-white/40">Confirmed</dt><dd>{operation.confirmed_at ?? "No data yet"}</dd></div>
              <div><dt className="text-white/40">Failed</dt><dd>{operation.failed_at ?? "No data yet"}</dd></div>
              <div><dt className="text-white/40">Last refresh</dt><dd>{operation.last_status_refreshed_at ?? "No data yet"}</dd></div>
            </dl>
          </Card>
          {metadataEntries(operation.safe_metadata).length ? (
            <Card>
              <h2 className="text-xl font-semibold text-white">Issuance metadata</h2>
              <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                {metadataEntries(operation.safe_metadata).map(([key, value]) => (
                  <div key={key} className="rounded-xl border border-white/10 bg-white/[0.04] p-3">
                    <dt className="text-white/40">{labelFromKey(key)}</dt>
                    <dd className="mt-1 break-words text-white/75">{Array.isArray(value) ? `${value.length} item${value.length === 1 ? "" : "s"}` : String(value)}</dd>
                  </div>
                ))}
              </dl>
            </Card>
          ) : null}
          {operation.can_view_raw_response ? (
            <Card>
              <h2 className="text-xl font-semibold text-white">Staff response details</h2>
              <pre className="mt-4 overflow-auto rounded-xl bg-black/25 p-4 text-xs text-white/65">{JSON.stringify(operation.raw_response ?? {}, null, 2)}</pre>
            </Card>
          ) : null}
        </div>
      ) : null}
    </Shell>
  );
}
