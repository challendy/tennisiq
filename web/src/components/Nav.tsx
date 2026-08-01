"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";

export function Nav() {
  const { user, logout } = useAuth();
  return (
    <header className="mb-6 flex items-center justify-between gap-3">
      <Link href="/" className="flex items-center gap-2">
        <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--lime)] text-lg font-black text-[var(--ink)]">
          TQ
        </span>
        <div>
          <div className="text-lg font-bold tracking-tight">TennisIQ</div>
          <div className="text-xs text-white/50">Why it happened. What to fix.</div>
        </div>
      </Link>
      <nav className="flex flex-wrap items-center gap-2 text-sm">
        {user ? (
          <>
            <Link className="btn-ghost" href="/upload">
              Analyze
            </Link>
            <Link className="btn-ghost" href="/progress">
              Progress
            </Link>
            <Link className="btn-ghost" href="/practice">
              Practice
            </Link>
            <button className="btn-ghost" onClick={logout} type="button">
              Sign out
            </button>
          </>
        ) : (
          <>
            <Link className="btn-ghost" href="/login">
              Log in
            </Link>
            <Link className="btn-primary" href="/register">
              Get started
            </Link>
          </>
        )}
      </nav>
    </header>
  );
}
