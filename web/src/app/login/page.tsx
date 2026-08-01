"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { login } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const { setUser } = useAuth();
  const router = useRouter();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError("");
    const fd = new FormData(e.currentTarget);
    try {
      const user = await login(String(fd.get("email")), String(fd.get("password")));
      setUser(user);
      router.push("/upload");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-md card p-6">
      <h1 className="mb-1 text-2xl font-bold">Welcome back</h1>
      <p className="mb-6 text-sm text-white/55">Log in to continue improving.</p>
      <form className="space-y-4" onSubmit={onSubmit}>
        <label className="block space-y-1 text-sm">
          <span>Email</span>
          <input className="input" name="email" type="email" required />
        </label>
        <label className="block space-y-1 text-sm">
          <span>Password</span>
          <input className="input" name="password" type="password" required minLength={8} />
        </label>
        {error && <p className="text-sm text-red-300">{error}</p>}
        <button className="btn-primary w-full" disabled={loading} type="submit">
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <p className="mt-4 text-center text-sm text-white/50">
        New here? <Link className="text-[var(--lime)]" href="/register">Create an account</Link>
      </p>
    </div>
  );
}
