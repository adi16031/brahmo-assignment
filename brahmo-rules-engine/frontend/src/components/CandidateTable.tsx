"use client";

import { CandidateNode, NodeType } from "@/lib/types";
import { NODE_TYPE_COLOR } from "@/lib/palette";

const TYPE_ORDER: NodeType[] = ["CONSTRAINT", "DECISION", "ANTI_PATTERN", "FACT"];

function TypeBadge({ type }: { type: NodeType }) {
  const c = NODE_TYPE_COLOR[type];
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium text-white"
      style={{ backgroundColor: c.light }}
    >
      {c.label}
    </span>
  );
}

export default function CandidateTable({ nodes }: { nodes: CandidateNode[] }) {
  const grouped = TYPE_ORDER.map((type) => ({
    type,
    items: nodes.filter((n) => n.type === type),
  })).filter((g) => g.items.length > 0);

  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-neutral-700 dark:text-neutral-200">
          Candidate Set ({nodes.length} nodes)
        </h3>
        <div className="flex gap-2">
          {TYPE_ORDER.map((t) => (
            <TypeBadge key={t} type={t} />
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-4">
        {grouped.map((group) => (
          <div key={group.type}>
            <div className="mb-1.5 flex items-center gap-2">
              <TypeBadge type={group.type} />
              <span className="text-xs text-neutral-400">
                {group.items.length} node{group.items.length !== 1 ? "s" : ""}
              </span>
            </div>
            <div className="flex flex-col gap-1.5">
              {group.items.map((node) => (
                <div
                  key={node.id}
                  className="rounded-md border border-neutral-100 p-2.5 text-sm dark:border-neutral-800"
                >
                  <div className="flex items-start justify-between gap-3">
                    <span className="font-medium text-neutral-800 dark:text-neutral-100">
                      {node.title}
                    </span>
                    <span className="shrink-0 text-xs tabular-nums text-neutral-400">
                      importance {node.importance.toFixed(2)}
                    </span>
                  </div>
                  <p className="mt-1 line-clamp-2 text-xs text-neutral-500 dark:text-neutral-400">
                    {node.content}
                  </p>
                  <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-0.5 text-[11px] text-neutral-400">
                    <span>zone {node.zone === 2 ? "GLOBAL" : "ADDRESSED"}</span>
                    <span>distance {node.distance_from_entry}</span>
                    <span>{node.compression_hint}</span>
                    <span>level {node.hierarchy_level}</span>
                    {node.department && <span>dept: {node.department}</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
        {nodes.length === 0 && (
          <p className="text-sm text-neutral-400">No nodes in the candidate set.</p>
        )}
      </div>
    </div>
  );
}
