"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";

export default function HomePage() {
  const { user } = useAuth();
  return (
    <div className="grid gap-8 md:grid-cols-[1.2fr_0.8fr] md:items-center">
      <section className="space-y-5">
        <p className="inline-flex rounded-full border border-[var(--lime)]/40 bg-[var(--lime)]/10 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-[var(--lime)]">
          MVP · Stroke analysis
        </p>
        <h1 className="text-4xl font-black leading-tight tracking-tight md:text-5xl">
          Professional coaching from ordinary phone video.
        </h1>
        <p className="max-w-xl text-lg text-white/70">
          Upload a serve, forehand, backhand, volley, or overhead. TennisIQ grades
          every phase, shows you the overlay, and names the single highest-impact fix.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link className="btn-primary" href={user ? "/upload" : "/register"}>
            {user ? "Analyze a stroke" : "Create free account"}
          </Link>
          <Link className="btn-ghost" href="/progress">
            View progress
          </Link>
        </div>
      </section>
      <section className="card space-y-4 p-6">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-white/50">
          The loop
        </h2>
        <ol className="space-y-3 text-sm">
          {[
            "Record a single stroke from the side",
            "Get grade, phase scores, and visual overlay",
            "Hear the one correction that matters most",
            "Practice a plan built from your weaknesses",
            "Compare sessions and watch the score move",
          ].map((step, i) => (
            <li key={step} className="flex gap-3">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--lime)]/20 text-xs font-bold text-[var(--lime)]">
                {i + 1}
              </span>
              <span className="pt-1 text-white/85">{step}</span>
            </li>
          ))}
        </ol>
        <p className="text-xs text-white/40">Free plan · 3 analyses / month</p>
      </section>
    </div>
  );
}
