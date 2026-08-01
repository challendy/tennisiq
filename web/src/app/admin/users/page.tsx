"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  adminListUsers,
  adminResetQuota,
  adminSetPlan,
  type AdminUser,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function AdminUsersPage() {
  const { user, ready } = useAuth();
  const router = useRouter();
  const [q, setQ] = useState("");
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!user) return;
    try {
      setError("");
      const data = await adminListUsers(user.token, q);
      setUsers(data.users);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load users");
    }
  }, [user, q]);

  useEffect(() => {
    if (!ready) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    if (!user.isAdmin) {
      router.replace("/");
      return;
    }
    void load();
  }, [ready, user, router, load]);

  async function setPlan(u: AdminUser, plan: "Free" | "Premium") {
    if (!user) return;
    if (!confirm(`Set ${u.email} to ${plan}?`)) return;
    setBusy(u.id);
    try {
      await adminSetPlan(user.token, u.id, plan);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Plan update failed");
    } finally {
      setBusy(null);
    }
  }

  async function resetQuota(u: AdminUser) {
    if (!user) return;
    if (!confirm(`Reset quota for ${u.email}?`)) return;
    setBusy(u.id);
    try {
      await adminResetQuota(user.token, u.id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Reset failed");
    } finally {
      setBusy(null);
    }
  }

  if (!ready || !user?.isAdmin) return null;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Users</h1>
          <p className="text-sm text-white/55">Set plan and reset monthly quota.</p>
        </div>
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            void load();
          }}
        >
          <input
            className="input max-w-xs"
            placeholder="Search email"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          <button className="btn-primary" type="submit">
            Search
          </button>
        </form>
      </div>

      {error && <p className="text-red-300">{error}</p>}

      <div className="card overflow-x-auto">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="border-b border-white/10 text-white/50">
            <tr>
              <th className="px-3 py-2 font-medium">Email</th>
              <th className="px-3 py-2 font-medium">Name</th>
              <th className="px-3 py-2 font-medium">Plan</th>
              <th className="px-3 py-2 font-medium">Quota</th>
              <th className="px-3 py-2 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-b border-white/5">
                <td className="px-3 py-3">
                  {u.email}
                  {u.isAdmin && (
                    <span className="ml-2 rounded bg-[var(--lime)]/20 px-1.5 py-0.5 text-xs text-[var(--lime)]">
                      admin
                    </span>
                  )}
                </td>
                <td className="px-3 py-3">{u.displayName}</td>
                <td className="px-3 py-3">{u.plan}</td>
                <td className="px-3 py-3">
                  {u.analysesUsed}
                  {u.analysesLimit == null ? " / ∞" : ` / ${u.analysesLimit}`}
                </td>
                <td className="px-3 py-3">
                  <div className="flex flex-wrap gap-1">
                    <button
                      className="btn-ghost !px-2 !py-1 text-xs"
                      type="button"
                      disabled={busy === u.id || u.plan === "Premium"}
                      onClick={() => void setPlan(u, "Premium")}
                    >
                      Premium
                    </button>
                    <button
                      className="btn-ghost !px-2 !py-1 text-xs"
                      type="button"
                      disabled={busy === u.id || u.plan === "Free"}
                      onClick={() => void setPlan(u, "Free")}
                    >
                      Free
                    </button>
                    <button
                      className="btn-ghost !px-2 !py-1 text-xs"
                      type="button"
                      disabled={busy === u.id}
                      onClick={() => void resetQuota(u)}
                    >
                      Reset quota
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {users.length === 0 && (
              <tr>
                <td className="px-3 py-6 text-white/50" colSpan={5}>
                  No users found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
