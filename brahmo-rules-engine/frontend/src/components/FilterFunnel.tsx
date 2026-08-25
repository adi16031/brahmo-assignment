"use client";

import { Funnel } from "@/lib/types";

interface Stage {
  key: keyof Funnel;
  label: string;
}

const STAGES: Stage[] = [
  { key: "total_nodes", label: "Total graph" },
  { key: "after_bfs", label: "BFS reachable" },
  { key: "after_zone2", label: "+ Zone 2 (global)" },
  { key: "after_check1", label: "Check 1 — Isolation" },
  { key: "after_check2", label: "Check 2 — Compliance" },
  { key: "after_check3", label: "Check 3 — Permission" },
  { key: "after_check4", label: "Check 4 — Temporal" },
  { key: "after_check5", label: "Check 5 — Derivability (final)" },
];

export default function FilterFunnel({ funnel }: { funnel: Funnel }) {
  const max = funnel.total_nodes || 1;

  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
      <h3 className="mb-3 text-sm font-semibold text-neutral-700 dark:text-neutral-200">
        Filter Funnel
      </h3>
      <div className="flex flex-col gap-2">
        {STAGES.map((stage, i) => {
          const value = funnel[stage.key];
          const prevValue = i > 0 ? funnel[STAGES[i - 1].key] : value;
          const removed = i > 0 ? prevValue - value : 0;
          const widthPct = Math.max((value / max) * 100, value > 0 ? 2 : 0);
          const isFinal = stage.key === "after_check5";
          return (
            <div key={stage.key} className="flex items-center gap-3">
              <div className="w-44 shrink-0 text-right text-xs text-neutral-500 dark:text-neutral-400">
                {stage.label}
              </div>
              <div className="relative h-6 flex-1 rounded bg-neutral-100 dark:bg-neutral-800">
                <div
                  className="h-6 rounded transition-all duration-500"
                  style={{
                    width: `${widthPct}%`,
                    backgroundColor: isFinal ? "#0ca30c" : "#2a78d6",
                  }}
                />
              </div>
              <div className="w-14 shrink-0 text-sm font-semibold tabular-nums text-neutral-800 dark:text-neutral-100">
                {value}
              </div>
              <div className="w-20 shrink-0 text-xs tabular-nums text-neutral-400">
                {removed > 0 ? `-${removed}` : ""}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
