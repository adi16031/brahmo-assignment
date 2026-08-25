// Validated categorical palette (light/dark), fixed hue order — see dataviz skill.
// Node types are assigned a hue by fixed order, never cycled/reassigned by rank.
import { NodeType } from "./types";

export const NODE_TYPE_COLOR: Record<NodeType, { light: string; dark: string; label: string }> = {
  CONSTRAINT: { light: "#2a78d6", dark: "#3987e5", label: "Constraint" }, // slot 1 blue
  DECISION: { light: "#eb6834", dark: "#d95926", label: "Decision" }, // slot 2 orange
  ANTI_PATTERN: { light: "#1baf7a", dark: "#199e70", label: "Anti-Pattern" }, // slot 3 aqua
  FACT: { light: "#eda100", dark: "#c98500", label: "Fact" }, // slot 4 yellow
};

export const SEQUENTIAL_BLUE = { light: "#2a78d6", dark: "#3987e5" };

export const STATUS = {
  good: "#0ca30c",
  warning: "#fab219",
  critical: "#d03b3b",
};

export const INK = {
  primary: { light: "#0b0b0b", dark: "#ffffff" },
  secondary: { light: "#52514e", dark: "#c3c2b7" },
  muted: { light: "#898781", dark: "#898781" },
  gridline: { light: "#e1e0d9", dark: "#2c2c2a" },
};
