"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { ProductNav } from "@/components/nav";
import { Card, EmptyState, Shell, StatusBadge } from "@/components/ui";
import { apiGet } from "@/lib/api";
import type { PropertyRecord } from "@/types/api";

export default function PropertyDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [property, setProperty] = useState<PropertyRecord | null>(null);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    apiGet<PropertyRecord>(`/api/properties/${id}/`)
      .then(setProperty)
      .catch(() => setNotFound(true));
  }, [id]);

  return (
    <Shell>
      <ProductNav />
      {notFound ? <EmptyState title="Property not available." detail="Draft properties are only visible to their issuer." /> : null}
      {property ? (
        <div className="space-y-6">
          <header className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h1 className="text-4xl font-semibold text-white">{property.title}</h1>
              <p className="mt-2 text-white/55">{property.address}</p>
            </div>
            <StatusBadge tone={property.status === "active" || property.status === "tokenized" ? "good" : "neutral"}>{property.status_display}</StatusBadge>
          </header>
          <Card>
            <p className="text-white/65">{property.description || "No description provided."}</p>
            <dl className="mt-6 grid gap-4 text-sm sm:grid-cols-3">
              <div><dt className="text-white/40">Estimated value</dt><dd>{property.estimated_value ?? "No data yet"}</dd></div>
              <div><dt className="text-white/40">Total shares</dt><dd>{property.total_shares}</dd></div>
              <div><dt className="text-white/40">Documents</dt><dd>{property.document_count}</dd></div>
              <div><dt className="text-white/40">Tokenization</dt><dd>{property.tokenization.status_display}</dd></div>
              <div><dt className="text-white/40">Txid</dt><dd className="break-all">{property.tokenization.txid ?? "No data yet"}</dd></div>
              <div><dt className="text-white/40">Asset ID</dt><dd className="break-all">{property.tokenization.asset_id ?? "No data yet"}</dd></div>
            </dl>
          </Card>
          {property.documents?.length ? (
            <Card>
              <h2 className="text-xl font-semibold text-white">Documents</h2>
              <div className="mt-4 grid gap-3">
                {property.documents.map((doc) => (
                  <div key={doc.id} className="rounded-xl border border-white/10 bg-white/[0.04] p-4">
                    <div className="font-medium text-white">{doc.document_type || "Document"}</div>
                    <div className="mt-1 break-all text-xs text-white/50">{doc.document_hash || "Hash pending"}</div>
                  </div>
                ))}
              </div>
            </Card>
          ) : (
            <EmptyState title="No documents uploaded yet." />
          )}
          {property.tokenization_operations?.length ? (
            <Card>
              <h2 className="text-xl font-semibold text-white">Tokenization operations</h2>
              <div className="mt-4 grid gap-3">
                {property.tokenization_operations.map((operation) => (
                  <Link key={operation.id} href={`/tokenization/operations/${operation.id}`} className="rounded-xl border border-white/10 bg-white/[0.04] p-4 transition hover:border-gold/40">
                    <div className="font-medium text-white">{operation.asset_symbol}</div>
                    <div className="mt-1 text-sm text-white/50">{operation.status}</div>
                  </Link>
                ))}
              </div>
            </Card>
          ) : (
            <EmptyState title="No tokenization operations yet." />
          )}
        </div>
      ) : null}
    </Shell>
  );
}
