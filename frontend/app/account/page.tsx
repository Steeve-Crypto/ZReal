"use client";

import { useEffect, useState } from "react";
import { ProductNav } from "@/components/nav";
import { Card, EmptyState, Shell, StatusBadge } from "@/components/ui";
import { ApiError, apiGet, apiJson, djangoLoginUrl } from "@/lib/api";
import type { CurrentUser } from "@/types/api";

type RoleStatus = {
  role: "investor" | "issuer" | "admin";
  is_issuer: boolean;
  is_investor: boolean;
};

export default function AccountPage() {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [role, setRole] = useState<RoleStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function load() {
    try {
      const [currentUser, currentRole] = await Promise.all([
        apiGet<CurrentUser>("/api/me/"),
        apiGet<RoleStatus>("/api/role/")
      ]);
      setUser(currentUser);
      setRole(currentRole);
      setError(null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) setError("Sign in through Django to use the product frontend.");
      else setError("Could not load profile state.");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function updateRole(nextRole: RoleStatus["role"]) {
    setSaving(true);
    try {
      const updated = await apiJson<RoleStatus>("/api/role/", "PATCH", { role: nextRole });
      setRole(updated);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update role.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Shell>
      <ProductNav />
      <header className="mb-8">
        <h1 className="text-4xl font-semibold text-white">Account</h1>
        <p className="mt-2 text-white/55">Django session state and role selection for the Next product UI.</p>
      </header>
      {error ? (
        <EmptyState title={error} detail={`Login URL: ${djangoLoginUrl("/account")}`} />
      ) : null}
      {user && role ? (
        <div className="grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
          <Card>
            <h2 className="text-xl font-semibold text-white">{user.username}</h2>
            <p className="mt-1 text-sm text-white/55">{user.email || "No email on file"}</p>
            <div className="mt-5">
              <StatusBadge tone={user.is_staff ? "good" : "neutral"}>{user.is_staff ? "Staff" : "Product user"}</StatusBadge>
            </div>
          </Card>
          <Card>
            <h2 className="text-xl font-semibold text-white">Role</h2>
            <p className="mt-1 text-sm text-white/55">Choose how this account should use ZReal.</p>
            <div className="mt-5 flex flex-wrap gap-3">
              {(["issuer", "investor"] as const).map((option) => (
                <button
                  key={option}
                  disabled={saving || role.role === option}
                  onClick={() => void updateRole(option)}
                  className="rounded-xl border border-white/10 bg-white/[0.06] px-5 py-3 text-sm font-semibold text-white transition hover:border-gold/50 disabled:cursor-not-allowed disabled:border-gold/40 disabled:text-gold"
                >
                  {role.role === option ? `Current: ${option}` : `Use as ${option}`}
                </button>
              ))}
            </div>
          </Card>
        </div>
      ) : null}
    </Shell>
  );
}
