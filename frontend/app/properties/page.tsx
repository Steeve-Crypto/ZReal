"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ProductNav } from "@/components/nav";
import { Card, EmptyState, Shell, StatusBadge } from "@/components/ui";
import { apiGet } from "@/lib/api";
import type { PropertyRecord } from "@/types/api";

export default function PropertyBrowsePage() {
  const [properties, setProperties] = useState<PropertyRecord[]>([]);

  useEffect(() => {
    apiGet<{ properties: PropertyRecord[] }>("/api/properties/browse/")
      .then((data) => setProperties(data.properties))
      .catch(() => setProperties([]));
  }, []);

  return (
    <Shell>
      <ProductNav />
      <header className="mb-8">
        <h1 className="text-4xl font-semibold text-white">Properties</h1>
        <p className="mt-2 text-white/55">Explore properties that have completed issuer preparation.</p>
      </header>
      {properties.length ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {properties.map((property) => (
            <Link key={property.id} href={`/properties/${property.id}`}>
              <Card className="h-full transition hover:border-gold/40">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h2 className="text-lg font-semibold text-white">{property.title}</h2>
                    <p className="mt-1 text-sm text-white/55">{property.address}</p>
                  </div>
                  <StatusBadge tone="good">{property.status_display}</StatusBadge>
                </div>
                <dl className="mt-6 grid grid-cols-2 gap-3 text-sm">
                  <div><dt className="text-white/40">Estimated value</dt><dd>{property.estimated_value ?? "No data yet"}</dd></div>
                  <div><dt className="text-white/40">Shares</dt><dd>{property.total_shares}</dd></div>
                </dl>
              </Card>
            </Link>
          ))}
        </div>
      ) : (
        <EmptyState title="No properties are available yet." detail="New opportunities will appear here after issuer preparation is complete." />
      )}
    </Shell>
  );
}
