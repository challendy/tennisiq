"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { compare, getProgress, listAnalyses } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function ProgressPage() {
  const { user, ready } = useAuth();
  const router = useRouter();
  const [progress, setProgress] = useState<Awaited<ReturnType<typeof getProgress>> | null>(null);
  const [analyses, setAnalyses] = useState<Awaited<ReturnType<typeof listAnalyses>>>([]);
  const [a, setA] = useState("");
  const [b, setB] = useState("");
  const [cmp, setCmp] = useState<Awaited<ReturnType<typeof compare>> | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!ready) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    Promise.all([getProgress(user.token), listAnalyses(user.token)])
      .then(([p, list]) => {
        setProgress(p);
        setAnalyses(list);
        const sameStroke = list.filter((x) => x.status === "ok");
        if (sameStroke.length >= 2) {
          setA(sameStroke[1].id);
          setB(sameStroke[0].id);
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed"));
  }, [ready, user, router]);

  async function runCompare() {
    if (!user || !a || !b) return;
    setError("");
    try {
      setCmp(await compare(user.token, a, b));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Compare failed");
    }
  }

  if (!ready || !user) return null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Progress</h1>
        <p className="text-sm text-white/55">Your TennisIQ score and session history.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="card p-5">
          <div className="text-xs uppercase text-white/45">TennisIQ</div>
          <div className="text-4xl font-black text-[var(--lime)]">
            {progress?.tennisIqScore ?? "—"}
          </div>
        </div>
        <div className="card p-5">
          <div className="text-xs uppercase text-white/45">Analyses</div>
          <div className="text-4xl font-black">{progress?.totalAnalyses ?? 0}</div>
        </div>
        <div className="card p-5">
          <div className="text-xs uppercase text-white/45">Strokes tracked</div>
          <div className="text-4xl font-black">{progress?.strokes.length ?? 0}</div>
        </div>
      </div>

      <section className="card p-5">
        <h2 className="mb-3 font-semibold">Recent analyses</h2>
        <ul className="divide-y divide-white/10">
          {analyses.map((item) => (
            <li key={item.id} className="flex items-center justify-between gap-3 py-3 text-sm">
              <div>
                <div className="font-semibold capitalize">
                  {item.stroke} · {item.grade} ({item.overallScore})
                </div>
                <div className="text-white/45">{new Date(item.createdAt).toLocaleString()}</div>
              </div>
              <Link className="btn-ghost" href={`/analyses/${item.id}`}>
                Open
              </Link>
            </li>
          ))}
          {analyses.length === 0 && (
            <li className="py-4 text-white/50">No analyses yet. Upload a stroke to begin.</li>
          )}
        </ul>
      </section>

      <section className="card space-y-3 p-5">
        <h2 className="font-semibold">Compare two sessions</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <select className="input" value={a} onChange={(e) => setA(e.target.value)}>
            <option value="">Earlier analysis</option>
            {analyses.map((x) => (
              <option key={x.id} value={x.id}>
                {x.stroke} · {x.grade} · {new Date(x.createdAt).toLocaleDateString()}
              </option>
            ))}
          </select>
          <select className="input" value={b} onChange={(e) => setB(e.target.value)}>
            <option value="">Later analysis</option>
            {analyses.map((x) => (
              <option key={x.id} value={x.id}>
                {x.stroke} · {x.grade} · {new Date(x.createdAt).toLocaleDateString()}
              </option>
            ))}
          </select>
        </div>
        <button className="btn-primary" type="button" onClick={runCompare}>
          Compare
        </button>
        {error && <p className="text-sm text-red-300">{error}</p>}
        {cmp && (
          <div className="space-y-2 pt-2">
            <p className="text-sm">
              Overall delta:{" "}
              <span className="font-bold text-[var(--lime)]">
                {cmp.overallDelta > 0 ? "+" : ""}
                {cmp.overallDelta.toFixed(1)}
              </span>
            </p>
            <ul className="space-y-1 text-sm">
              {cmp.phases.map((p) => (
                <li key={p.phase} className="flex justify-between capitalize">
                  <span>{p.phase.replaceAll("_", " ")}</span>
                  <span>
                    {p.a.toFixed(0)} → {p.b.toFixed(0)}{" "}
                    <span className="text-white/45">({p.direction})</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>
    </div>
  );
}
