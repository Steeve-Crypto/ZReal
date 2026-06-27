"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ProductNav } from "@/components/nav";
import { Card, Shell } from "@/components/ui";
import { PropertyForm, cleanPropertyPayload, valuesFromProperty } from "@/components/property-form";
import { ApiError, apiJson, userFacingError } from "@/lib/api";
import type { PropertyMutationResponse } from "@/types/api";

export default function NewPropertyPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  return (
    <Shell>
      <ProductNav />
      <header className="mb-8">
        <h1 className="text-4xl font-semibold text-white">Create Property</h1>
        <p className="mt-2 text-white/55">Issuer-only. Enter property information you are authorized to manage.</p>
      </header>
      <Card>
        <PropertyForm
          initialValues={valuesFromProperty(null)}
          submitLabel="Create property"
          error={error}
          onSubmit={async (values, context) => {
            setError(null);
            try {
              const payload = {
                ...cleanPropertyPayload(values),
                ...(context.enrichment && context.selectedCandidate ? {
                  enrichment_status: context.enrichment.status,
                  enrichment_provider: context.enrichment.provider,
                  enrichment_candidate: context.selectedCandidate,
                  enrichment_candidates: context.enrichment.candidates,
                  enrichment_warnings: context.enrichment.warnings,
                  enrichment_blockers: context.enrichment.blockers
                } : {})
              };
              const response = await apiJson<PropertyMutationResponse>("/api/properties/new/", "POST", payload);
              router.push(`/properties/${response.property.id}`);
            } catch (err) {
              if (err instanceof ApiError && err.status === 403) {
                setError("Issuer access is required. Sign in with an issuer account to create properties.");
              } else {
                setError(userFacingError(err, "Could not create property."));
              }
            }
          }}
        />
      </Card>
    </Shell>
  );
}
