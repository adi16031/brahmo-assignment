"use client";

import { useState } from "react";
import { CandidateSetResponse, UserSummary } from "@/lib/types";
import { runPipeline } from "@/lib/api";

interface Props {
  users: UserSummary[];
}

const DEPT_WATCHLIST = ["cardiology", "paediatrics", "icu", "medicine"];

export default function ComparisonView({ users }: Props) {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [results, setResults] = useState<Record<string, CandidateSetResponse>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggle(id: string) {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  }

  async function runAll() {
    setLoading(true);
    setError(null);
    try {
      const entries = await Promise.all(
        selectedIds.map(async (id) => [id, await runPipeline(id)] as const)
      );
      setResults(Object.fromEntries(entries));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to run comparison");
    } finally {
      setLoading(false);
    }
  }

  const activeResults = selectedIds
    .map((id) => results[id])
    .filter((r): r is CandidateSetResponse => Boolean(r));

  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
      <h3 className="mb-3 text-sm font-semibold text-neutral-700 dark:text-neutral-200">
        Same Graph, Different Users
      </h3>

      <div className="mb-3 flex flex-wrap gap-3">
        {users.map((u) => (
          <label key={u.id} className="flex items-center gap-1.5 text-xs">
            <input
              type="checkbox"
              checked={selectedIds.includes(u.id)}
              onChange={() => toggle(u.id)}
            />
            {u.name}
          </label>
        ))}
        <button
          onClick={runAll}
          disabled={selectedIds.length === 0 || loading}
          className="ml-2 rounded-md bg-[#2a78d6] px-3 py-1 text-xs font-medium text-white disabled:opacity-40"
        >
          {loading ? "Running…" : "Run Comparison"}
        </button>
      </div>

      {error && <p className="text-xs text-[#d03b3b]">{error}</p>}

      {activeResults.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[480px] border-collapse text-xs">
            <thead>
              <tr className="border-b border-neutral-200 text-left text-neutral-500 dark:border-neutral-800">
                <th className="py-2 pr-4">Metric</th>
                {activeResults.map((r) => (
                  <th key={r.user_id} className="py-2 pr-4 font-medium text-neutral-700 dark:text-neutral-200">
                    {r.user_name}
                    <div className="font-normal text-neutral-400">
                      {r.role}, L{r.ceiling_level}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="tabular-nums">
              <Row label="BFS reach" values={activeResults.map((r) => r.funnel.after_bfs)} />
              <Row label="+ Zone 2" values={activeResults.map((r) => r.funnel.after_zone2)} />
              <Row
                label="After 5-check (final)"
                values={activeResults.map((r) => r.funnel.after_check5)}
                bold
              />
              <Row
                label="Pipeline time (ms)"
                values={activeResults.map((r) => r.pipeline_timing.total_ms)}
              />
              {DEPT_WATCHLIST.map((dept) => (
                <tr key={dept} className="border-b border-neutral-100 dark:border-neutral-800">
                  <td className="py-1.5 pr-4 text-neutral-500">Sees {dept} nodes</td>
                  {activeResults.map((r) => {
                    const sees = r.candidate_set.some((c) => c.department === dept);
                    return (
                      <td key={r.user_id} className="py-1.5 pr-4">
                        <span style={{ color: sees ? "#0ca30c" : "#d03b3b" }}>
                          {sees ? "✓" : "✗"}
                        </span>
                      </td>
                    );
                  })}
                </tr>
              ))}
              <tr>
                <td className="py-1.5 pr-4 text-neutral-500">Sees drug-safety (Zone 2) nodes</td>
                {activeResults.map((r) => {
                  const sees = r.candidate_set.some((c) => c.zone === 2);
                  return (
                    <td key={r.user_id} className="py-1.5 pr-4">
                      <span style={{ color: sees ? "#0ca30c" : "#d03b3b" }}>
                        {sees ? "✓" : "✗"}
                      </span>
                    </td>
                  );
                })}
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Row({
  label,
  values,
  bold,
}: {
  label: string;
  values: number[];
  bold?: boolean;
}) {
  return (
    <tr className="border-b border-neutral-100 dark:border-neutral-800">
      <td className="py-1.5 pr-4 text-neutral-500">{label}</td>
      {values.map((v, i) => (
        <td
          key={i}
          className={`py-1.5 pr-4 ${bold ? "font-semibold text-neutral-800 dark:text-neutral-100" : ""}`}
        >
          {v}
        </td>
      ))}
    </tr>
  );
}
