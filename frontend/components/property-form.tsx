"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import type { PropertyRecord } from "@/types/api";

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
    size_sqm: property ? String(property.size_sqm) : "",
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

export function PropertyForm({
  initialValues,
  submitLabel,
  onSubmit,
  error
}: {
  initialValues: PropertyFormValues;
  submitLabel: string;
  onSubmit: (values: PropertyFormValues) => Promise<void>;
  error?: string | null;
}) {
  const [values, setValues] = useState(initialValues);
  const [submitting, setSubmitting] = useState(false);

  function update(field: keyof PropertyFormValues, value: string) {
    setValues((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    try {
      await onSubmit(values);
    } finally {
      setSubmitting(false);
    }
  }

  const inputClass = "rounded-xl border border-white/10 bg-white/[0.06] px-4 py-3 text-white outline-none transition focus:border-gold/60";

  return (
    <form onSubmit={handleSubmit} className="grid gap-4">
      {error ? <div className="rounded-xl border border-red-400/25 bg-red-400/10 px-4 py-3 text-sm text-red-100">{error}</div> : null}
      <label className="grid gap-2">
        <span className="text-sm text-white/60">Title</span>
        <input required value={values.title} onChange={(event) => update("title", event.target.value)} className={inputClass} />
      </label>
      <label className="grid gap-2">
        <span className="text-sm text-white/60">Address</span>
        <input required value={values.address} onChange={(event) => update("address", event.target.value)} className={inputClass} />
      </label>
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
          <input required type="number" min="0" step="0.01" value={values.size_sqm} onChange={(event) => update("size_sqm", event.target.value)} className={inputClass} />
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
          <input required type="number" min="1" value={values.total_shares} onChange={(event) => update("total_shares", event.target.value)} className={inputClass} />
        </label>
      </div>
      <button disabled={submitting} className="rounded-xl bg-gold px-5 py-3 font-semibold text-ink transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50">
        {submitting ? "Saving..." : submitLabel}
      </button>
    </form>
  );
}
