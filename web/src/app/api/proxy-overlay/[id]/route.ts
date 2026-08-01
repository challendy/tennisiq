import { NextRequest } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:5129";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const token = req.nextUrl.searchParams.get("token");
  if (!token) {
    return new Response("Unauthorized", { status: 401 });
  }
  const upstream = await fetch(`${API_BASE}/api/overlays/${id}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!upstream.ok) {
    return new Response(await upstream.text(), { status: upstream.status });
  }
  return new Response(upstream.body, {
    status: 200,
    headers: {
      "Content-Type": "video/mp4",
      "Cache-Control": "private, max-age=3600",
    },
  });
}
