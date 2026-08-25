"use client";

import { useEffect, useState } from "react";
import { CandidateSetResponse, UserSummary } from "@/lib/types";
import { fetchUsers, runPipeline } from "@/lib/api";
import UserSelector from "@/components/UserSelector";
import FilterFunnel from "@/components/FilterFunnel";
import DAGViewer from "@/components/DAGViewer";
import CandidateTable from "@/components/CandidateTable";
import ComparisonView from "@/components/ComparisonView";

export default function Home() {
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [zone2Enabled, setZone2Enabled] = useState(true);
  const [result, setResult] = useState<CandidateSetResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"pipeline" | "comparison">("pipeline");
  const [usersError, setUsersError] = useState<string | null>(null);

  useEffect(() => {
    fetchUsers()
      .then(setUsers)
      .catch((e) =>
        setUsersError(
          e instanceof Error
            ? `${e.message} — is the backend running and .env.local filled in?`
            : "Failed to load users"
        )
      );
  }, []);

  async function handleRun() {
    if (!selectedUserId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await runPipeline(selectedUserId, zone2Enabled);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Pipeline run failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex max-w-6xl flex-1 flex-col gap-4 p-6">
      <header>
        <h1 className="text-xl font-bold text-neutral-900 dark:text-neutral-50">
          BRAHMO Rules Engine — BFS + 5-Check Filter Pipeline
        </h1>
        <p className="text-sm text-neutral-500">
          Zero LLM. Deterministic. Silent exclusion. Same code path for every user.
        </p>
      </header>

      {usersError && (
        <div className="rounded-md border border-[#d03b3b]/30 bg-[#d03b3b]/5 p-3 text-sm text-[#d03b3b]">
          {usersError}
        </div>
      )}

      <nav className="flex gap-1 border-b border-neutral-200 dark:border-neutral-800">
        {(["pipeline", "comparison"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-2 text-sm font-medium ${
              tab === t
                ? "border-b-2 border-[#2a78d6] text-[#2a78d6]"
                : "text-neutral-500"
            }`}
          >
            {t === "pipeline" ? "Pipeline" : "Comparison"}
          </button>
        ))}
      </nav>

      {tab === "pipeline" && (
        <>
          <UserSelector
            users={users}
            selectedUserId={selectedUserId}
            onSelect={setSelectedUserId}
            zone2Enabled={zone2Enabled}
            onZone2Toggle={setZone2Enabled}
            onRun={handleRun}
            loading={loading}
          />

          {error && (
            <div className="rounded-md border border-[#d03b3b]/30 bg-[#d03b3b]/5 p-3 text-sm text-[#d03b3b]">
              {error}
            </div>
          )}

          {result && (
            <>
              <div className="flex flex-wrap items-center gap-4 rounded-lg border border-neutral-200 bg-white p-3 text-sm dark:border-neutral-800 dark:bg-neutral-900">
                <span>
                  Entry point: <strong>{result.entry_point_name}</strong> (
                  {result.entry_point})
                </span>
                <span>
                  Pipeline time:{" "}
                  <strong
                    style={{
                      color: result.pipeline_timing.total_ms < 500 ? "#0ca30c" : "#d03b3b",
                    }}
                  >
                    {result.pipeline_timing.total_ms}ms
                  </strong>
                </span>
                <span className="text-neutral-400">Zero LLM calls · Deterministic</span>
              </div>

              <FilterFunnel funnel={result.funnel} />

              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <DAGViewer dag={result.dag} />
                <CandidateTable nodes={result.candidate_set} />
              </div>
            </>
          )}
        </>
      )}

      {tab === "comparison" && <ComparisonView users={users} />}
    </main>
  );
}
