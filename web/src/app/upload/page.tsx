"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { getJob, me, uploadVideo } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const STROKES = ["forehand", "backhand", "serve", "volley", "overhead"];

export default function UploadPage() {
  const { user, ready } = useAuth();
  const router = useRouter();
  const [stroke, setStroke] = useState("forehand");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [quota, setQuota] = useState<string>("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!ready) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    me(user.token)
      .then((m) => {
        setQuota(
          m.analysesLimit == null
            ? "Premium · unlimited"
            : `${m.analysesUsed}/${m.analysesLimit} free analyses used this month`,
        );
      })
      .catch(() => undefined);
  }, [ready, user, router]);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!user) return;
    const fd = new FormData(e.currentTarget);
    const file = fd.get("file");
    if (!(file instanceof File) || !file.size) {
      setError("Choose a video file.");
      return;
    }
    setBusy(true);
    setError("");
    setStatus("Uploading…");
    try {
      const { jobId } = await uploadVideo(user.token, file, stroke);
      setStatus("Analyzing — pose, phases, coaching…");
      for (;;) {
        await new Promise((r) => setTimeout(r, 1200));
        const job = await getJob(user.token, jobId);
        if (job.status === "Succeeded" && job.analysisId) {
          router.push(`/analyses/${job.analysisId}`);
          return;
        }
        if (job.status === "Failed") {
          throw new Error(job.error || "Analysis failed");
        }
        setStatus(`Analyzing… (${job.status.toLowerCase()}, attempt ${job.attempts || 1})`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      setStatus("");
    } finally {
      setBusy(false);
    }
  }

  if (!ready || !user) return null;

  return (
    <div className="mx-auto max-w-xl space-y-4">
      <div>
        <h1 className="text-3xl font-bold">Analyze a stroke</h1>
        <p className="text-sm text-white/55">
          Side view, full body in frame, one complete stroke. {quota}
        </p>
      </div>
      <form className="card space-y-4 p-6" onSubmit={onSubmit}>
        <label className="block space-y-1 text-sm">
          <span>Stroke</span>
          <select
            className="input"
            value={stroke}
            onChange={(e) => setStroke(e.target.value)}
          >
            {STROKES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="block space-y-1 text-sm">
          <span>Video</span>
          <input
            className="input file:mr-3 file:rounded-lg file:border-0 file:bg-[var(--lime)] file:px-3 file:py-1 file:text-sm file:font-semibold file:text-[var(--ink)]"
            name="file"
            type="file"
            accept="video/*"
            required
            capture="environment"
          />
        </label>
        {status && <p className="text-sm text-[var(--lime)]">{status}</p>}
        {error && <p className="text-sm text-red-300">{error}</p>}
        <button className="btn-primary w-full" disabled={busy} type="submit">
          {busy ? "Working…" : "Upload & analyze"}
        </button>
      </form>
    </div>
  );
}
