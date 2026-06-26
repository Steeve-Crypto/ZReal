"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ProductNav } from "@/components/nav";
import { Card, Shell } from "@/components/ui";
import { PropertyForm, cleanPropertyPayload, valuesFromProperty } from "@/components/property-form";
import { ApiError, apiJson, djangoLoginUrl } from "@/lib/api";
import type { PropertyRecord } from "@/types/api";

export default function NewPropertyPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  return (
    <Shell>
      <ProductNav />
      <header className="mb-8">
        <h1 className="text-4xl font-semibold text-white">Create Property</h1>
        <p className="mt-2 text-white/55">Issuer-only. Enter real property information you are authorized to manage.</p>
      </header>
      <Card>
        <PropertyForm
          initialValues={valuesFromProperty(null)}
          submitLabel="Create property"
          error={error}
          onSubmit={async (values) => {
            setError(null);
            try {
              const property = await apiJson<PropertyRecord>("/api/properties/new/", "POST", cleanPropertyPayload(values));
              router.push(`/properties/${property.id}`);
            } catch (err) {
              if (err instanceof ApiError && err.status === 403) {
                setError(`Issuer role and Django login are required. Login: ${djangoLoginUrl("/properties/new")}`);
              } else {
                setError(err instanceof Error ? err.message : "Could not create property.");
              }
            }
          }}
        />
      </Card>
    </Shell>
  );
}
