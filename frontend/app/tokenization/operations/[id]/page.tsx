"use client";

import { use, useEffect, useState } from "react";
import { ProductNav } from "@/components/nav";
import { Card, EmptyState, Shell, StatusBadge } from "@/components/ui";
import { apiGet } from "@/lib/api";
import type { TokenizationOperation } from "@/types/api";

export default function TokenizationOperationPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [operation, setOperation] = useState<TokenizationOperation | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    apiGet<TokenizationOperation>(`/api/tokenization/operations/${id}/`)
      .then(setOperation)
      .catch(() => setError(true));
  }, [id]);

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
            <StatusBadge tone={operation.status === "confirmed" ? "good" : operation.status === "failed" ? "bad" : "warn"}>{operation.status}</StatusBadge>
          </header>
          <Card>
            <dl className="grid gap-4 text-sm sm:grid-cols-2">
              <div><dt className="text-white/40">Backend</dt><dd>{operation.backend}</dd></div>
              <div><dt className="text-white/40">Issuer address</dt><dd>{operation.issuer_zaddr_masked ?? "No data yet"}</dd></div>
              <div><dt className="text-white/40">Operation ID</dt><dd className="break-all">{operation.operation_id ?? "No data yet"}</dd></div>
              <div><dt className="text-white/40">Txid</dt><dd className="break-all">{operation.txid ?? "No data yet"}</dd></div>
              <div><dt className="text-white/40">Asset ID</dt><dd className="break-all">{operation.asset_id ?? "No data yet"}</dd></div>
              <div><dt className="text-white/40">Error</dt><dd>{operation.error ?? "No error recorded"}</dd></div>
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
