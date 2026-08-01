"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { register } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function RegisterPage() {
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
      const user = await register({
        email: String(fd.get("email")),
        password: String(fd.get("password")),
        displayName: String(fd.get("displayName")),
        handedness: String(fd.get("handedness") || "right"),
      });
      setUser(user);
      router.push("/upload");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-md card p-6">
      <h1 className="mb-1 text-2xl font-bold">Start free</h1>
      <p className="mb-6 text-sm text-white/55">3 analyses a month. No card required.</p>
      <form className="space-y-4" onSubmit={onSubmit}>
        <label className="block space-y-1 text-sm">
          <span>Display name</span>
          <input className="input" name="displayName" required />
        </label>
        <label className="block space-y-1 text-sm">
          <span>Email</span>
          <input className="input" name="email" type="email" required />
        </label>
        <label className="block space-y-1 text-sm">
          <span>Password</span>
          <input className="input" name="password" type="password" required minLength={8} />
        </label>
        <label className="block space-y-1 text-sm">
          <span>Handedness</span>
          <select className="input" name="handedness" defaultValue="right">
            <option value="right">Right</option>
            <option value="left">Left</option>
          </select>
        </label>
        {error && <p className="text-sm text-red-300">{error}</p>}
        <button className="btn-primary w-full" disabled={loading} type="submit">
          {loading ? "Creating…" : "Create account"}
        </button>
      </form>
      <p className="mt-4 text-center text-sm text-white/50">
        Already have an account? <Link className="text-[var(--lime)]" href="/login">Log in</Link>
      </p>
    </div>
  );
}
