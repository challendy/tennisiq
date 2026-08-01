"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { createPracticePlan } from "@/lib/api";
import { useAuth } from "@/lib/auth";

function PracticeInner() {
  const { user, ready } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const analysisId = params.get("analysisId") ?? undefined;
  const [plan, setPlan] = useState<Awaited<ReturnType<typeof createPracticePlan>> | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!ready) return;
    if (!user) router.replace("/login");
  }, [ready, user, router]);

  async function generate() {
    if (!user) return;
    setLoading(true);
    setError("");
    try {
      setPlan(await createPracticePlan(user.token, analysisId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create plan");
    } finally {
      setLoading(false);
    }
  }

  if (!ready || !user) return null;

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <div>
        <h1 className="text-3xl font-bold">Practice planner</h1>
        <p className="text-sm text-white/55">
          Built from your latest weaknesses — one focused session.
        </p>
      </div>
      <button className="btn-primary" type="button" onClick={generate} disabled={loading}>
        {loading ? "Building…" : "Generate session"}
      </button>
      {error && <p className="text-sm text-red-300">{error}</p>}
      {plan && (
        <section className="card space-y-4 p-6">
          <h2 className="text-xl font-bold">{plan.goal}</h2>
          <ol className="space-y-3">
            {plan.items.map((item, i) => (
              <li key={`${item.section}-${i}`} className="rounded-xl border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase tracking-wider text-[var(--lime)]">
                  {item.section}
                </div>
                <div className="font-semibold">{item.drill}</div>
                <div className="text-sm text-white/55">
                  {item.reps} reps · ~{item.minutes} min
                </div>
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}

export default function PracticePage() {
  return (
    <Suspense fallback={<p className="text-white/60">Loading…</p>}>
      <PracticeInner />
    </Suspense>
  );
}
