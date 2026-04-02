export type DefectClass =
  | "open_circuit"
  | "short"
  | "mousebite"
  | "spur"
  | "spurious_copper"
  | "pin_hole"

export interface Detection {
  class: DefectClass
  confidence: number
  bbox: [number, number, number, number] // [x1, y1, x2, y2]
}

export interface AnalyzeResponse {
  detections: Detection[]
  image_size: { width: number; height: number }
}

export interface RepairSheet {
  component: string
  defect_type: string
  severity: "low" | "medium" | "high"
  steps: string[]
  estimated_cost: string
  difficulty: number // 1 to 5
}

export interface DiagnoseResponse {
  repair_sheet: RepairSheet
}

export const DEFECT_COLORS: Record<DefectClass, string> = {
  open_circuit: "#ef4444",
  short: "#f97316",
  mousebite: "#eab308",
  spur: "#3b82f6",
  spurious_copper: "#8b5cf6",
  pin_hole: "#6b7280",
}

export const DEFECT_LABELS: Record<DefectClass, string> = {
  open_circuit: "Open Circuit",
  short: "Short",
  mousebite: "Mousebite",
  spur: "Spur",
  spurious_copper: "Spurious Copper",
  pin_hole: "Pin Hole",
}
