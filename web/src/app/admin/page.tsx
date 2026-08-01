"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth";

export default function AdminIndexPage() {
  const { user, ready } = useAuth();
  const router = useRouter();

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
    router.replace("/admin/users");
  }, [ready, user, router]);

  return <p className="text-white/60">Opening admin…</p>;
}
