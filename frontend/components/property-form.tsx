"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { apiJson, userFacingError } from "@/lib/api";
import type { PropertyEnrichment, PropertyMutationResponse, PropertyRecord } from "@/types/api";

export type PropertyFormValues = {
  title: string;
  description: string;
  address: string;
  latitude: string;
  longitude: string;
  size_sqm: string;
  bedrooms: string;
  bathrooms: string;
  estimated_value: string;
  total_shares: string;
};

export function valuesFromProperty(property?: PropertyRecord | null): PropertyFormValues {
  return {
    title: property?.title ?? "",
    description: property?.description ?? "",
    address: property?.address ?? "",
    latitude: property?.latitude ?? "",
    longitude: property?.longitude ?? "",
    size_sqm: property?.size_sqm ? String(property.size_sqm) : "",
    bedrooms: property?.bedrooms ? String(property.bedrooms) : "",
    bathrooms: property?.bathrooms ? String(property.bathrooms) : "",
    estimated_value: property?.estimated_value ?? "",
    total_shares: property ? String(property.total_shares) : ""
  };
}

export function cleanPropertyPayload(values: PropertyFormValues) {
  return {
    title: values.title.trim(),
    description: values.description.trim(),
    address: values.address.trim(),
    latitude: values.latitude.trim() || null,
    longitude: values.longitude.trim() || null,
    size_sqm: values.size_sqm.trim(),
    bedrooms: values.bedrooms.trim() || null,
    bathrooms: values.bathrooms.trim() || null,
    estimated_value: values.estimated_value.trim() || null,
    total_shares: values.total_shares.trim()
  };
}

export type PropertyFormSubmitContext = {
  enrichment: PropertyEnrichment | null;
  selectedCandidate: Record<string, unknown> | null;
};

function enrichmentSourceLabel(provider?: string | null) {
  if (!provider) return null;
  const labels: Record<string, string> = {
    mock: "Address reference",
    fixture: "Address reference",
    census: "US Census Geocoder",
    regrid: "Parcel data provider",
    opencage: "Geocoding provider",
    google: "Geocoding provider"
  };
  return labels[provider] ?? "Property data provider";
}

export function PropertyForm({
  initialValues,
  propertyId,
  initialEnrichment,
  submitLabel,
  onSubmit,
  error
}: {
  initialValues: PropertyFormValues;
  propertyId?: number;
  initialEnrichment?: PropertyEnrichment | null;
  submitLabel: string;
  onSubmit: (values: PropertyFormValues, context: PropertyFormSubmitContext) => Promise<void>;
  error?: string | null;
}) {
  const [values, setValues] = useState(initialValues);
  const [enrichment, setEnrichment] = useState<PropertyEnrichment | null>(initialEnrichment ?? null);
  const [selectedCandidate, setSelectedCandidate] = useState(0);
  const [autofillError, setAutofillError] = useState<string | null>(null);
  const [autofilling, setAutofilling] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  function update(field: keyof PropertyFormValues, value: string) {
    setValues((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    try {
      await onSubmit(values, {
        enrichment,
        selectedCandidate: enrichment?.candidates?.[selectedCandidate] ?? null
      });
    } finally {
      setSubmitting(false);
    }
  }

  function candidateValue(candidate: Record<string, unknown>, key: string) {
    const value = candidate[key];
    return value === null || value === undefined ? "" : String(value);
  }

  function applyCandidate(candidate: Record<string, unknown>) {
    setValues((current) => ({
      ...current,
      address: candidateValue(candidate, "normalized_address") || current.address,
      latitude: candidateValue(candidate, "latitude") || current.latitude,
      longitude: candidateValue(candidate, "longitude") || current.longitude,
      size_sqm: candidateValue(candidate, "building_area") || current.size_sqm,
      estimated_value: candidateValue(candidate, "assessed_value") || current.estimated_value
    }));
  }

  async function autofillPropertyDetails() {
    setAutofillError(null);
    setAutofilling(true);
    try {
      if (propertyId) {
        const response = await apiJson<PropertyMutationResponse & { enrichment: PropertyEnrichment }>(`/api/properties/${propertyId}/enrich/`, "POST", {
          address: values.address
        });
        setEnrichment(response.enrichment);
        if (response.enrichment.candidates[0]) applyCandidate(response.enrichment.candidates[0]);
      } else {
        const response = await apiJson<{ status: string; provider: string; candidates: Array<Record<string, unknown>>; warnings: string[]; blockers: string[] }>(
          "/api/properties/resolve-address/",
          "POST",
          { address: values.address }
        );
        const next: PropertyEnrichment = {
          status: response.candidates.length > 1 ? "needs_review" : response.status === "enriched" ? "enriched" : "failed",
          is_confirmed: false,
          provider: response.provider,
          normalized_address: candidateValue(response.candidates[0] ?? {}, "normalized_address") || null,
          match_confidence: candidateValue(response.candidates[0] ?? {}, "match_confidence") || null,
          warnings: response.warnings,
          blockers: response.blockers,
          candidates: response.candidates
        };
        setEnrichment(next);
        if (response.candidates[0]) applyCandidate(response.candidates[0]);
      }
      setSelectedCandidate(0);
    } catch (err) {
      setAutofillError(userFacingError(err, "Could not autofill property details."));
    } finally {
      setAutofilling(false);
    }
  }

  async function confirmAutofill() {
    if (!propertyId) return;
    setConfirming(true);
    setAutofillError(null);
    try {
      const response = await apiJson<PropertyMutationResponse & { enrichment: PropertyEnrichment }>(`/api/properties/${propertyId}/confirm-enrichment/`, "POST", {
        normalized_address: values.address,
        latitude: values.latitude || null,
        longitude: values.longitude || null,
        building_area: values.size_sqm || null,
        assessed_value: values.estimated_value || null
      });
      setEnrichment(response.enrichment);
    } catch (err) {
      setAutofillError(userFacingError(err, "Could not confirm autofill."));
    } finally {
      setConfirming(false);
    }
  }

  const inputClass = "rounded-xl border border-white/10 bg-white/[0.06] px-4 py-3 text-white outline-none transition focus:border-gold/60";

  return (
    <form onSubmit={handleSubmit} className="grid gap-4">
      {error ? <div className="rounded-xl border border-red-400/25 bg-red-400/10 px-4 py-3 text-sm text-red-100">{error}</div> : null}
      <label className="grid gap-2">
        <span className="text-sm text-white/60">Title</span>
        <input value={values.title} onChange={(event) => update("title", event.target.value)} className={inputClass} />
      </label>
      <label className="grid gap-2">
        <span className="text-sm text-white/60">Address</span>
        <input required value={values.address} onChange={(event) => update("address", event.target.value)} className={inputClass} />
      </label>
      <div className="rounded-xl border border-white/10 bg-white/[0.035] p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="text-sm font-medium text-white">Property data autofill</div>
            <div className="mt-1 text-xs text-white/50">
              {enrichment?.provider ? `${enrichmentSourceLabel(enrichment.provider)} - ${enrichment.status.replaceAll("_", " ")}` : "Resolve address, then review editable fields before saving."}
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" disabled={!values.address.trim() || autofilling} onClick={() => void autofillPropertyDetails()} className="rounded-xl border border-gold/35 bg-gold/10 px-4 py-2 text-sm font-semibold text-gold disabled:cursor-not-allowed disabled:opacity-50">
              {autofilling ? "Autofilling..." : "Autofill property details"}
            </button>
            {propertyId && enrichment && enrichment.status !== "not_started" && !enrichment.is_confirmed ? (
              <button type="button" disabled={confirming} onClick={() => void confirmAutofill()} className="rounded-xl bg-gold px-4 py-2 text-sm font-semibold text-ink disabled:cursor-not-allowed disabled:opacity-50">
                {confirming ? "Confirming..." : "Confirm autofill"}
              </button>
            ) : null}
          </div>
        </div>
        {autofillError ? <div className="mt-3 rounded-xl border border-red-400/25 bg-red-400/10 px-3 py-2 text-sm text-red-100">{autofillError}</div> : null}
        {enrichment?.warnings?.length ? (
          <div className="mt-3 grid gap-2 text-sm text-amber-100">
            {enrichment.warnings.map((warning) => <div key={warning} className="rounded-xl border border-amber-300/20 bg-amber-300/10 px-3 py-2">{warning}</div>)}
          </div>
        ) : null}
        {enrichment?.candidates?.length ? (
          <div className="mt-4 grid gap-3">
            {enrichment.candidates.length > 1 ? (
              <label className="grid gap-2">
                <span className="text-sm text-white/60">Candidate</span>
                <select
                  value={selectedCandidate}
                  onChange={(event) => {
                    const next = Number(event.target.value);
                    setSelectedCandidate(next);
                    applyCandidate(enrichment.candidates[next]);
                  }}
                  className={inputClass}
                >
                  {enrichment.candidates.map((candidate, index) => (
                    <option key={`${candidateValue(candidate, "normalized_address")}-${index}`} value={index}>
                      {candidateValue(candidate, "normalized_address") || `Candidate ${index + 1}`}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
            <dl className="grid gap-3 text-sm sm:grid-cols-3">
              <div><dt className="text-white/40">Confidence</dt><dd>{candidateValue(enrichment.candidates[selectedCandidate], "match_confidence") || "No data yet"}</dd></div>
              <div><dt className="text-white/40">Parcel/APN</dt><dd>{candidateValue(enrichment.candidates[selectedCandidate], "parcel_id") || candidateValue(enrichment.candidates[selectedCandidate], "apn") || "No data yet"}</dd></div>
              <div><dt className="text-white/40">County</dt><dd>{candidateValue(enrichment.candidates[selectedCandidate], "county") || "No data yet"}</dd></div>
            </dl>
          </div>
        ) : null}
      </div>
      <label className="grid gap-2">
        <span className="text-sm text-white/60">Description</span>
        <textarea value={values.description} onChange={(event) => update("description", event.target.value)} className={inputClass} rows={4} />
      </label>
      <div className="grid gap-4 md:grid-cols-2">
        <label className="grid gap-2">
          <span className="text-sm text-white/60">Latitude</span>
          <input value={values.latitude} onChange={(event) => update("latitude", event.target.value)} className={inputClass} />
        </label>
        <label className="grid gap-2">
          <span className="text-sm text-white/60">Longitude</span>
          <input value={values.longitude} onChange={(event) => update("longitude", event.target.value)} className={inputClass} />
        </label>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <label className="grid gap-2">
          <span className="text-sm text-white/60">Size sqm</span>
          <input type="number" min="0" step="0.01" value={values.size_sqm} onChange={(event) => update("size_sqm", event.target.value)} className={inputClass} />
        </label>
        <label className="grid gap-2">
          <span className="text-sm text-white/60">Bedrooms</span>
          <input type="number" min="0" value={values.bedrooms} onChange={(event) => update("bedrooms", event.target.value)} className={inputClass} />
        </label>
        <label className="grid gap-2">
          <span className="text-sm text-white/60">Bathrooms</span>
          <input type="number" min="0" value={values.bathrooms} onChange={(event) => update("bathrooms", event.target.value)} className={inputClass} />
        </label>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <label className="grid gap-2">
          <span className="text-sm text-white/60">Estimated value</span>
          <input type="number" min="0" step="0.01" value={values.estimated_value} onChange={(event) => update("estimated_value", event.target.value)} className={inputClass} />
        </label>
        <label className="grid gap-2">
          <span className="text-sm text-white/60">Total shares</span>
          <input type="number" min="1" value={values.total_shares} onChange={(event) => update("total_shares", event.target.value)} className={inputClass} />
        </label>
      </div>
      <button disabled={submitting} className="rounded-xl bg-gold px-5 py-3 font-semibold text-ink transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50">
        {submitting ? "Saving..." : submitLabel}
      </button>
    </form>
  );
}
