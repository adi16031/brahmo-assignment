export interface PipelineTiming {
  permission_compile_ms: number;
  entry_resolve_ms: number;
  bfs_ms: number;
  zone2_inject_ms: number;
  fetch_nodes_ms: number;
  check1_isolation_ms: number;
  check2_compliance_ms: number;
  check3_permission_ms: number;
  check4_temporal_ms: number;
  check5_derivability_ms: number;
  total_ms: number;
}

export interface Funnel {
  total_nodes: number;
  after_bfs: number;
  after_zone2: number;
  after_check1: number;
  after_check2: number;
  after_check3: number;
  after_check4: number;
  after_check5: number;
}

export type NodeType = "CONSTRAINT" | "DECISION" | "ANTI_PATTERN" | "FACT";
export type CompressionHint = "FULL" | "COMPRESSED" | "CONSTRAINT_ONLY";

export interface CandidateNode {
  id: string;
  type: NodeType;
  title: string;
  content: string;
  importance: number;
  zone: number;
  hierarchy_level: number;
  department: string | null;
  distance_from_entry: number;
  compression_hint: CompressionHint;
}

export interface DagLevelView {
  id: string;
  level_name: string;
  level_number: number;
  department: string | null;
  zone: number;
  parent_ids: string[];
  reachable: boolean;
  distance: number | null;
  reachable_via: "BFS" | "ZONE2" | null;
  is_entry: boolean;
}

export interface CandidateSetResponse {
  user_id: string;
  user_name: string;
  role: string;
  ceiling_level: number;
  entry_point: string;
  entry_point_name?: string | null;
  pipeline_timing: PipelineTiming;
  funnel: Funnel;
  candidate_set: CandidateNode[];
  dag: DagLevelView[];
}

export interface UserSummary {
  id: string;
  name: string;
  role: string;
  department: string;
  ceiling_level: number;
  write_ceiling: number | null;
  compliance_clearance: string[];
}
