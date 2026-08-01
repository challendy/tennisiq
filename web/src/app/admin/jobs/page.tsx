"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  adminCancelJob,
  adminListJobs,
  adminRetryJob,
  type AdminJob,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";

const STATUSES = ["", "Pending", "Running", "Succeeded", "Failed"] as const;

export default function AdminJobsPage() {
  const { user, ready } = useAuth();
  const router = useRouter();
  const [status, setStatus] = useState("");
  const [jobs, setJobs] = useState<AdminJob[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!user) return;
    try {
      setError("");
      const data = await adminListJobs(user.token, status);
      setJobs(data.jobs);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load jobs");
    }
  }, [user, status]);

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

  async function retry(job: AdminJob) {
    if (!user) return;
    if (!confirm(`Retry job ${job.id.slice(0, 8)}…?`)) return;
    setBusy(job.id);
    try {
      await adminRetryJob(user.token, job.id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Retry failed");
    } finally {
      setBusy(null);
    }
  }

  async function cancel(job: AdminJob) {
    if (!user) return;
    if (!confirm(`Cancel job ${job.id.slice(0, 8)}…?`)) return;
    setBusy(job.id);
    try {
      await adminCancelJob(user.token, job.id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Cancel failed");
    } finally {
      setBusy(null);
    }
  }

  if (!ready || !user?.isAdmin) return null;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Jobs</h1>
          <p className="text-sm text-white/55">Retry failed analyses or cancel stuck work.</p>
        </div>
        <label className="text-sm text-white/60">
          Status{" "}
          <select
            className="input ml-2 max-w-[10rem]"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            {STATUSES.map((s) => (
              <option key={s || "all"} value={s}>
                {s || "All"}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error && <p className="text-red-300">{error}</p>}

      <div className="card overflow-x-auto">
        <table className="w-full min-w-[860px] text-left text-sm">
          <thead className="border-b border-white/10 text-white/50">
            <tr>
              <th className="px-3 py-2 font-medium">Job</th>
              <th className="px-3 py-2 font-medium">Status</th>
              <th className="px-3 py-2 font-medium">User</th>
              <th className="px-3 py-2 font-medium">Stroke</th>
              <th className="px-3 py-2 font-medium">Attempts</th>
              <th className="px-3 py-2 font-medium">Error</th>
              <th className="px-3 py-2 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((j) => (
              <tr key={j.id} className="border-b border-white/5 align-top">
                <td className="px-3 py-3 font-mono text-xs">{j.id.slice(0, 8)}</td>
                <td className="px-3 py-3">{j.status}</td>
                <td className="px-3 py-3">{j.userEmail}</td>
                <td className="px-3 py-3 capitalize">{j.stroke}</td>
                <td className="px-3 py-3">{j.attempts}</td>
                <td className="max-w-[14rem] truncate px-3 py-3 text-xs text-white/55" title={j.error ?? ""}>
                  {j.error || "—"}
                </td>
                <td className="px-3 py-3">
                  <div className="flex flex-wrap gap-1">
                    <button
                      className="btn-ghost !px-2 !py-1 text-xs"
                      type="button"
                      disabled={busy === j.id || j.status !== "Failed"}
                      onClick={() => void retry(j)}
                    >
                      Retry
                    </button>
                    <button
                      className="btn-ghost !px-2 !py-1 text-xs"
                      type="button"
                      disabled={busy === j.id || j.status === "Succeeded"}
                      onClick={() => void cancel(j)}
                    >
                      Cancel
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {jobs.length === 0 && (
              <tr>
                <td className="px-3 py-6 text-white/50" colSpan={7}>
                  No jobs found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
