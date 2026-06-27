"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ProductNav } from "@/components/nav";
import { Card, EmptyState, Shell } from "@/components/ui";
import { PropertyForm, cleanPropertyPayload, valuesFromProperty } from "@/components/property-form";
import { apiGet, apiJson, userFacingError } from "@/lib/api";
import type { PropertyMutationResponse, PropertyRecord } from "@/types/api";

export default function EditPropertyPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [property, setProperty] = useState<PropertyRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [blocked, setBlocked] = useState<string | null>(null);

  useEffect(() => {
    apiGet<PropertyRecord>(`/api/properties/${id}/`)
      .then((record) => {
        if (!record.ownership.can_edit) {
          setBlocked("Only the issuer owner can edit this property.");
          return;
        }
        setProperty(record);
      })
      .catch(() => setBlocked("Property not available."));
  }, [id]);

  return (
    <Shell>
      <ProductNav />
      <header className="mb-8">
        <h1 className="text-4xl font-semibold text-white">Edit Property</h1>
        <p className="mt-2 text-white/55">Review and update issuer-owned property details.</p>
      </header>
      {blocked ? <EmptyState title={blocked} /> : null}
      {property ? (
        <Card>
          <PropertyForm
            initialValues={valuesFromProperty(property)}
            propertyId={property.id}
            initialEnrichment={property.enrichment}
            submitLabel="Save changes"
            error={error}
            onSubmit={async (values) => {
              setError(null);
              try {
                const response = await apiJson<PropertyMutationResponse>(`/api/properties/${id}/edit/`, "PATCH", cleanPropertyPayload(values));
                router.push(`/properties/${response.property.id}`);
              } catch (err) {
                setError(userFacingError(err, "Could not update property."));
              }
            }}
          />
        </Card>
      ) : null}
    </Shell>
  );
}
