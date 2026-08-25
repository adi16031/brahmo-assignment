"use client";

import { UserSummary } from "@/lib/types";

interface Props {
  users: UserSummary[];
  selectedUserId: string | null;
  onSelect: (userId: string) => void;
  zone2Enabled: boolean;
  onZone2Toggle: (enabled: boolean) => void;
  onRun: () => void;
  loading: boolean;
}

export default function UserSelector({
  users,
  selectedUserId,
  onSelect,
  zone2Enabled,
  onZone2Toggle,
  onRun,
  loading,
}: Props) {
  const selected = users.find((u) => u.id === selectedUserId);

  return (
    <div className="flex flex-wrap items-end gap-4 rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-neutral-500 dark:text-neutral-400">
          User
        </label>
        <select
          className="min-w-[280px] rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100"
          value={selectedUserId ?? ""}
          onChange={(e) => onSelect(e.target.value)}
        >
          <option value="" disabled>
            Select a user…
          </option>
          {users.map((u) => (
            <option key={u.id} value={u.id}>
              {u.name} — {u.role}, L{u.ceiling_level}, {u.department}
            </option>
          ))}
        </select>
      </div>

      {selected && (
        <div className="flex flex-col gap-1 text-xs text-neutral-500 dark:text-neutral-400">
          <span>
            Ceiling: L{selected.ceiling_level} · Write:{" "}
            {selected.write_ceiling ?? "none"} · Clearance:{" "}
            {selected.compliance_clearance.length
              ? selected.compliance_clearance.join(", ")
              : "none"}
          </span>
        </div>
      )}

      <label className="flex items-center gap-2 text-sm text-neutral-700 dark:text-neutral-300">
        <input
          type="checkbox"
          checked={zone2Enabled}
          onChange={(e) => onZone2Toggle(e.target.checked)}
          className="h-4 w-4 rounded border-neutral-300"
        />
        Zone 2 injection enabled
      </label>

      <button
        onClick={onRun}
        disabled={!selectedUserId || loading}
        className="ml-auto rounded-md bg-[#2a78d6] px-4 py-2 text-sm font-medium text-white transition-opacity disabled:opacity-40 dark:bg-[#3987e5]"
      >
        {loading ? "Running…" : "Run Pipeline"}
      </button>
    </div>
  );
}
