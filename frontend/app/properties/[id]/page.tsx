"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { ProductNav } from "@/components/nav";
import { Card, EmptyState, Shell, StatusBadge } from "@/components/ui";
import { ApiError, apiGet, apiJson, apiUpload } from "@/lib/api";
import type { PropertyMutationResponse, PropertyRecord, TokenizationMutationResponse } from "@/types/api";

export default function PropertyDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [property, setProperty] = useState<PropertyRecord | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [documentType, setDocumentType] = useState("Legal Document");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [issuerZaddr, setIssuerZaddr] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  async function loadProperty() {
    const record = await apiGet<PropertyRecord>(`/api/properties/${id}/`);
    setProperty(record);
  }

  useEffect(() => {
    loadProperty()
      .catch(() => setNotFound(true));
  }, [id]);

  async function uploadDocument() {
    if (!selectedFile) {
      setActionError("Choose a real document file first.");
      return;
    }
    setUploading(true);
    setActionError(null);
    setActionMessage(null);
    const formData = new FormData();
    formData.append("document", selectedFile);
    formData.append("document_type", documentType);
    try {
      const response = await apiUpload<PropertyMutationResponse>(`/api/properties/${id}/documents/upload/`, formData);
      setActionMessage(response.notifications.map((item) => item.message).join(" "));
      setSelectedFile(null);
      await loadProperty();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Document upload failed.");
    } finally {
      setUploading(false);
    }
  }

  async function issueTokenization() {
    setActionError(null);
    setActionMessage(null);
    if (!property?.readiness.ready_for_tokenization) {
      setActionError(property?.readiness.blocking_issues.join(" ") || "Property is not ready for tokenization.");
      return;
    }
    if (!issuerZaddr.trim()) {
      setActionError("Issuer shielded address is required.");
      return;
    }
    try {
      const response = await apiJson<TokenizationMutationResponse>(`/api/properties/${id}/tokenize/`, "POST", {
        issuer_zaddr: issuerZaddr.trim()
      });
      setActionMessage(response.notifications.map((item) => item.message).join(" "));
      await loadProperty();
    } catch (err) {
      if (err instanceof ApiError && err.data) {
        const data = err.data as { error?: string; readiness?: { blocking_issues?: string[] } };
        setActionError(data.error ?? data.readiness?.blocking_issues?.join(" ") ?? err.message);
      }
      else setActionError(err instanceof Error ? err.message : "Tokenization request failed.");
      await loadProperty();
    }
  }

  async function runLifecycleAction(path: string) {
    setActionError(null);
    setActionMessage(null);
    try {
      const response = await apiJson<PropertyMutationResponse>(path, "POST", {});
      setProperty(response.property);
      setActionMessage(response.notifications.map((item) => item.message).join(" "));
    } catch (err) {
      if (err instanceof ApiError && err.data) setActionError(JSON.stringify(err.data));
      else setActionError(err instanceof Error ? err.message : "Lifecycle action failed.");
      await loadProperty().catch(() => undefined);
    }
  }

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
            <div className="flex flex-wrap gap-2">
              {property.ownership.can_edit ? <Link href={`/properties/${property.id}/edit`} className="nav-pill">Edit</Link> : null}
              <StatusBadge tone={property.status === "active" || property.status === "tokenized" ? "good" : property.status === "tokenization_pending" ? "warn" : property.status === "archived" || property.status === "suspended" ? "bad" : "neutral"}>{property.status_display}</StatusBadge>
            </div>
          </header>
          {actionError ? <div className="rounded-xl border border-red-400/25 bg-red-400/10 px-4 py-3 text-sm text-red-100">{actionError}</div> : null}
          {actionMessage ? <div className="rounded-xl border border-emerald-400/25 bg-emerald-400/10 px-4 py-3 text-sm text-emerald-100">{actionMessage}</div> : null}
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
          {property.latest_tokenization_operation ? (
            <Card>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h2 className="text-xl font-semibold text-white">Latest Tokenization Operation</h2>
                  <p className="mt-1 text-sm text-white/55">{property.latest_tokenization_operation.asset_symbol}</p>
                </div>
                <StatusBadge tone={property.latest_tokenization_operation.status === "confirmed" ? "good" : property.latest_tokenization_operation.status === "failed" ? "bad" : "warn"}>
                  {property.latest_tokenization_operation.status}
                </StatusBadge>
              </div>
              <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-3">
                <div><dt className="text-white/40">Operation ID</dt><dd className="break-all">{property.latest_tokenization_operation.operation_id ?? "No data yet"}</dd></div>
                <div><dt className="text-white/40">Txid</dt><dd className="break-all">{property.latest_tokenization_operation.txid ?? "No data yet"}</dd></div>
                <div><dt className="text-white/40">Asset ID</dt><dd className="break-all">{property.latest_tokenization_operation.asset_id ?? "No data yet"}</dd></div>
                <div><dt className="text-white/40">Created</dt><dd>{property.latest_tokenization_operation.created_at ?? "No data yet"}</dd></div>
                <div><dt className="text-white/40">Last refresh</dt><dd>{property.latest_tokenization_operation.last_status_refreshed_at ?? "No data yet"}</dd></div>
                <div><dt className="text-white/40">Error</dt><dd>{property.latest_tokenization_operation.error ?? "No error recorded"}</dd></div>
              </dl>
            </Card>
          ) : null}
          <Card>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <h2 className="text-xl font-semibold text-white">Readiness</h2>
                <p className="mt-1 text-sm text-white/55">Next action: {property.readiness.next_action.replaceAll("_", " ")}</p>
              </div>
              <StatusBadge tone={property.readiness.ready_for_tokenization ? "good" : "warn"}>
                {property.readiness.ready_for_tokenization ? "Ready for tokenization" : "Blocked"}
              </StatusBadge>
            </div>
            <div className="mt-5 grid gap-3 md:grid-cols-2">
              {property.readiness.checks.map((check) => (
                <div key={check.key} className="rounded-xl border border-white/10 bg-white/[0.04] p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="font-medium text-white">{check.label}</div>
                    <StatusBadge tone={check.ok ? "good" : "bad"}>{check.ok ? "OK" : "Needed"}</StatusBadge>
                  </div>
                  {!check.ok ? <p className="mt-2 text-sm text-white/55">{check.detail}</p> : null}
                </div>
              ))}
            </div>
            {property.readiness.blocking_issues.length ? (
              <ul className="mt-5 grid gap-2 text-sm text-amber-100">
                {property.readiness.blocking_issues.map((issue) => (
                  <li key={issue} className="rounded-xl border border-amber-300/20 bg-amber-300/10 px-3 py-2">{issue}</li>
                ))}
              </ul>
            ) : null}
          </Card>
          {property.documents?.length ? (
            <Card>
              <h2 className="text-xl font-semibold text-white">Documents</h2>
              <div className="mt-4 grid gap-3">
                {property.documents.map((doc) => (
                  <div key={doc.id} className="rounded-xl border border-white/10 bg-white/[0.04] p-4">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <div className="font-medium text-white">{doc.document_type || "Document"}</div>
                        <div className="mt-1 break-all text-xs text-white/50">{doc.document_hash || "Hash pending"}</div>
                      </div>
                      <StatusBadge>{doc.processing_status}</StatusBadge>
                    </div>
                    {Object.keys(doc.safe_extracted_metadata).length ? (
                      <pre className="mt-3 overflow-auto rounded-xl bg-black/20 p-3 text-xs text-white/60">{JSON.stringify(doc.safe_extracted_metadata, null, 2)}</pre>
                    ) : null}
                  </div>
                ))}
              </div>
            </Card>
          ) : (
            <EmptyState title="No documents uploaded yet." />
          )}
          {property.ownership.can_upload_documents ? (
            <Card>
              <h2 className="text-xl font-semibold text-white">Upload Document</h2>
              <p className="mt-1 text-sm text-white/55">Upload a real PDF or image. The frontend displays hash/status and safe extracted metadata only.</p>
              <div className="mt-5 grid gap-4 md:grid-cols-[0.7fr_1.3fr_auto] md:items-end">
                <label className="grid gap-2">
                  <span className="text-sm text-white/60">Document type</span>
                  <input value={documentType} onChange={(event) => setDocumentType(event.target.value)} className="rounded-xl border border-white/10 bg-white/[0.06] px-4 py-3 text-white outline-none focus:border-gold/60" />
                </label>
                <label className="grid gap-2">
                  <span className="text-sm text-white/60">File</span>
                  <input type="file" accept=".pdf,.png,.jpg,.jpeg" onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)} className="rounded-xl border border-white/10 bg-white/[0.06] px-4 py-3 text-white" />
                </label>
                <button disabled={uploading} onClick={() => void uploadDocument()} className="rounded-xl bg-gold px-5 py-3 font-semibold text-ink disabled:cursor-not-allowed disabled:opacity-50">
                  {uploading ? "Uploading..." : "Upload"}
                </button>
              </div>
            </Card>
          ) : null}
          {property.ownership.can_tokenize ? (
            <Card>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h2 className="text-xl font-semibold text-white">ZSA Tokenization</h2>
                  <p className="mt-1 text-sm text-white/55">No fake issuance. Requests call the configured Django ZSA backend.</p>
                </div>
                <StatusBadge tone={property.readiness.zsa.ready ? "good" : "bad"}>{property.readiness.zsa.ready ? "Ready" : "ZSA backend is not configured."}</StatusBadge>
              </div>
              {!property.readiness.zsa.ready && property.readiness.zsa.missing?.length ? (
                <ul className="mt-4 grid gap-2 text-sm text-amber-100">
                  {property.readiness.zsa.missing.map((item) => <li key={item} className="rounded-xl border border-amber-300/20 bg-amber-300/10 px-3 py-2">{item}</li>)}
                </ul>
              ) : null}
              <div className="mt-5 grid gap-4 md:grid-cols-[1fr_auto] md:items-end">
                <label className="grid gap-2">
                  <span className="text-sm text-white/60">Issuer shielded address</span>
                  <input value={issuerZaddr} onChange={(event) => setIssuerZaddr(event.target.value)} className="rounded-xl border border-white/10 bg-white/[0.06] px-4 py-3 text-white outline-none focus:border-gold/60" />
                </label>
                <button disabled={!property.readiness.ready_for_tokenization} onClick={() => void issueTokenization()} className="rounded-xl bg-gold px-5 py-3 font-semibold text-ink disabled:cursor-not-allowed disabled:opacity-40">
                  Issue ZSA
                </button>
              </div>
            </Card>
          ) : null}
          {property.ownership.is_owner ? (
            <Card>
              <h2 className="text-xl font-semibold text-white">Available Actions</h2>
              <div className="mt-4 flex flex-wrap gap-3">
                {property.status === "tokenized" ? (
                  <button onClick={() => void runLifecycleAction(`/api/properties/${id}/activate/`)} className="rounded-xl bg-gold px-5 py-3 font-semibold text-ink">Activate</button>
                ) : null}
                {property.status === "active" ? (
                  <button onClick={() => void runLifecycleAction(`/api/properties/${id}/suspend/`)} className="rounded-xl border border-amber-300/30 bg-amber-300/10 px-5 py-3 font-semibold text-amber-100">Suspend</button>
                ) : null}
                {property.status !== "archived" ? (
                  <button onClick={() => void runLifecycleAction(`/api/properties/${id}/archive/`)} className="rounded-xl border border-white/15 bg-white/[0.06] px-5 py-3 font-semibold text-white">Archive</button>
                ) : null}
              </div>
            </Card>
          ) : null}
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
