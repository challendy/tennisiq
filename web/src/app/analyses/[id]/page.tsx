"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getAnalysis, overlaySrc } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Analysis = Awaited<ReturnType<typeof getAnalysis>>;

export default function AnalysisPage() {
  const { id } = useParams<{ id: string }>();
  const { user, ready } = useAuth();
  const router = useRouter();
  const [data, setData] = useState<Analysis | null>(null);
  const [error, setError] = useState("");
  const [speaking, setSpeaking] = useState(false);

  useEffect(() => {
    if (!ready) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    getAnalysis(user.token, id)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
  }, [ready, user, id, router]);

  function speak() {
    if (!data?.coachingScript || typeof window === "undefined") return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(data.coachingScript);
    u.rate = 1.02;
    u.onend = () => setSpeaking(false);
    setSpeaking(true);
    window.speechSynthesis.speak(u);
  }

  if (!ready || !user) return null;
  if (error) return <p className="text-red-300">{error}</p>;
  if (!data) return <p className="text-white/60">Loading analysis…</p>;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wider text-white/45">{data.stroke}</p>
          <h1 className="text-3xl font-bold">
            Grade {data.grade}{" "}
            <span className="text-white/50">· {data.overallScore}</span>
          </h1>
          <p className="text-sm text-white/55">
            Confidence {(data.confidence * 100).toFixed(0)}%
            {data.status !== "ok" ? " · quality gate triggered" : ""}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="btn-primary" type="button" onClick={speak} disabled={speaking}>
            {speaking ? "Speaking…" : "Play AI voice coach"}
          </button>
          <Link className="btn-ghost" href={`/practice?analysisId=${data.id}`}>
            Build practice plan
          </Link>
          <Link className="btn-ghost" href="/progress">
            Compare later
          </Link>
        </div>
      </div>

      {data.overlayUrl && (
        <div className="card overflow-hidden">
          <video
            className="aspect-video w-full bg-black"
            controls
            playsInline
            src={overlaySrc(data.id, user.token)}
          />
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <section className="card space-y-3 p-5">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-white/45">
            Highest-impact fix
          </h2>
          <p className="text-lg font-semibold text-[var(--lime)]">{data.topFix}</p>
          <p className="text-sm text-white/70">{data.coachingScript}</p>
        </section>
        <section className="card space-y-3 p-5">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-white/45">
            Phase breakdown
          </h2>
          <ul className="space-y-3">
            {data.phases.map((p) => (
              <li key={p.phase}>
                <div className="mb-1 flex justify-between text-sm">
                  <span className="capitalize">{p.phase.replaceAll("_", " ")}</span>
                  <span className="font-semibold">{p.score.toFixed(0)}</span>
                </div>
                <div className="phase-bar">
                  <span style={{ width: `${Math.min(100, p.score)}%` }} />
                </div>
                <p className="mt-1 text-xs text-white/50">{p.feedback}</p>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
