"use client";

import { DagLevelView } from "@/lib/types";

function nodeStyle(level: DagLevelView): { bg: string; text: string; label: string } {
  if (level.is_entry) return { bg: "#2a78d6", text: "#ffffff", label: "● entry" };
  if (level.reachable_via === "ZONE2") return { bg: "#eda100", text: "#ffffff", label: "◆ zone 2" };
  if (level.reachable_via === "BFS") return { bg: "#1baf7a", text: "#ffffff", label: "● reachable" };
  return { bg: "transparent", text: "#898781", label: "○ not reachable" };
}

export default function DAGViewer({ dag }: { dag: DagLevelView[] }) {
  const levels = Array.from(new Set(dag.map((d) => d.level_number))).sort((a, b) => a - b);

  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-neutral-700 dark:text-neutral-200">
          DAG Hierarchy
        </h3>
        <div className="flex gap-3 text-[11px] text-neutral-500">
          <span><span style={{ color: "#2a78d6" }}>●</span> entry</span>
          <span><span style={{ color: "#1baf7a" }}>●</span> BFS reachable</span>
          <span><span style={{ color: "#eda100" }}>◆</span> zone 2 (global)</span>
          <span><span style={{ color: "#c3c2b7" }}>○</span> not reachable</span>
        </div>
      </div>

      <div className="flex flex-col gap-2">
        {levels.map((levelNumber) => {
          const nodesAtLevel = dag.filter((d) => d.level_number === levelNumber);
          return (
            <div key={levelNumber} className="flex items-start gap-2">
              <div className="w-8 shrink-0 pt-1 text-right text-[11px] font-medium text-neutral-400">
                L{levelNumber}
              </div>
              <div className="flex flex-wrap gap-1.5">
                {nodesAtLevel.map((level) => {
                  const style = nodeStyle(level);
                  const border =
                    style.bg === "transparent" ? "1px dashed #c3c2b7" : "none";
                  return (
                    <span
                      key={level.id}
                      title={`${level.level_name}${
                        level.distance !== null ? ` — distance ${level.distance}` : ""
                      } — ${style.label}`}
                      className="rounded px-2 py-1 text-[11px] font-medium"
                      style={{
                        backgroundColor: style.bg,
                        color: style.bg === "transparent" ? style.text : "#fff",
                        border,
                        opacity: level.reachable || level.is_entry ? 1 : 0.55,
                      }}
                    >
                      {level.level_name}
                    </span>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
