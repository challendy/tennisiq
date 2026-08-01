const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:5129";

export type AuthUser = {
  token: string;
  userId: string;
  email: string;
  displayName: string;
  plan: string;
};

function authHeaders(token?: string): HeadersInit {
  const h: HeadersInit = {};
  if (token) h.Authorization = `Bearer ${token}`;
  return h;
}

async function parse<T>(res: Response): Promise<T> {
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const msg = data?.error ?? data?.detail ?? res.statusText;
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return data as T;
}

export async function register(body: {
  email: string;
  password: string;
  displayName: string;
  handedness?: string;
}): Promise<AuthUser> {
  const res = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await parse<{
    token: string;
    userId: string;
    email: string;
    displayName: string;
    plan: string;
  }>(res);
  return data;
}

export async function login(email: string, password: string): Promise<AuthUser> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  return parse(res);
}

export async function me(token: string) {
  const res = await fetch(`${API_BASE}/api/auth/me`, {
    headers: authHeaders(token),
  });
  return parse<{
    id: string;
    email: string;
    displayName: string;
    handedness: string;
    plan: string;
    analysesUsed: number;
    analysesLimit: number | null;
  }>(res);
}

export async function uploadVideo(
  token: string,
  file: File,
  stroke: string,
): Promise<{ videoId: string; jobId: string; status: string }> {
  const form = new FormData();
  form.append("file", file);
  form.append("stroke", stroke);
  const res = await fetch(`${API_BASE}/api/videos`, {
    method: "POST",
    headers: authHeaders(token),
    body: form,
  });
  return parse(res);
}

export async function getJob(token: string, jobId: string) {
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}`, {
    headers: authHeaders(token),
  });
  return parse<{
    jobId: string;
    videoId: string;
    status: string;
    attempts: number;
    error?: string;
    analysisId?: string;
  }>(res);
}

export async function listAnalyses(token: string) {
  const res = await fetch(`${API_BASE}/api/analyses`, {
    headers: authHeaders(token),
  });
  return parse<
    Array<{
      id: string;
      stroke: string;
      status: string;
      overallScore: number;
      grade: string;
      confidence: number;
      topFix: string;
      createdAt: string;
      videoId: string;
    }>
  >(res);
}

export async function getAnalysis(token: string, id: string) {
  const res = await fetch(`${API_BASE}/api/analyses/${id}`, {
    headers: authHeaders(token),
  });
  return parse<{
    id: string;
    videoId: string;
    stroke: string;
    status: string;
    overallScore: number;
    grade: string;
    confidence: number;
    topFix: string;
    coachingScript: string;
    overlayUrl: string | null;
    phases: Array<{ phase: string; score: number; feedback: string }>;
    result: unknown;
    createdAt: string;
  }>(res);
}

export function overlaySrc(analysisId: string, token: string) {
  // Video element can't set Authorization header; use a short-lived approach:
  // for MVP the API accepts the token as a query for overlays only via a proxy route.
  return `/api/proxy-overlay/${analysisId}?token=${encodeURIComponent(token)}`;
}

export async function getProgress(token: string) {
  const res = await fetch(`${API_BASE}/api/progress`, {
    headers: authHeaders(token),
  });
  return parse<{
    tennisIqScore: number;
    totalAnalyses: number;
    strokes: Array<{
      stroke: string;
      latest: number;
      best: number;
      count: number;
      history: Array<{ createdAt: string; overallScore: number; grade: string; id: string }>;
    }>;
  }>(res);
}

export async function compare(token: string, a: string, b: string) {
  const res = await fetch(
    `${API_BASE}/api/analyses/compare?a=${a}&b=${b}`,
    { headers: authHeaders(token) },
  );
  return parse<{
    stroke: string;
    a: { id: string; overallScore: number; grade: string; createdAt: string };
    b: { id: string; overallScore: number; grade: string; createdAt: string };
    overallDelta: number;
    phases: Array<{
      phase: string;
      a: number;
      b: number;
      delta: number;
      direction: string;
    }>;
  }>(res);
}

export async function createPracticePlan(token: string, analysisId?: string) {
  const qs = analysisId ? `?analysisId=${analysisId}` : "";
  const res = await fetch(`${API_BASE}/api/practice/plans${qs}`, {
    method: "POST",
    headers: authHeaders(token),
  });
  return parse<{
    id: string;
    goal: string;
    generatedFromAnalysisId: string;
    items: Array<{ section: string; drill: string; reps: number; minutes: number }>;
    createdAt: string;
  }>(res);
}

export { API_BASE };
