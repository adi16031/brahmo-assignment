import { CandidateSetResponse, UserSummary } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function fetchUsers(): Promise<UserSummary[]> {
  const res = await fetch(`${API_BASE}/api/users`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch users (${res.status})`);
  return res.json();
}

export async function runPipeline(
  userId: string,
  zone2Enabled: boolean = true
): Promise<CandidateSetResponse> {
  const res = await fetch(`${API_BASE}/api/pipeline/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, zone2_enabled: zone2Enabled }),
    cache: "no-store",
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Pipeline run failed (${res.status}): ${detail}`);
  }
  return res.json();
}
