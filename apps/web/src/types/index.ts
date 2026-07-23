export type DefectClass =
  | "short"
  | "spur"
  | "spurious_copper"
  | "open"
  | "mousebite"
  | "hole_breakout"
  | "conductor_scratch"
  | "conductor_foreign_object"
  | "base_material_foreign_object"
  | "anomaly"

export interface Detection {
  class_id: number
  class_name: DefectClass
  confidence: number
  bbox: [number, number, number, number] // [x1, y1, x2, y2]
}

export interface AnalyzeResponse {
  success: boolean
  detections: Detection[]
  image_annotated: string | null
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
  short: "#f97316",
  spur: "#3b82f6",
  spurious_copper: "#8b5cf6",
  open: "#ef4444",
  mousebite: "#eab308",
  hole_breakout: "#ec4899",
  conductor_scratch: "#14b8a6",
  conductor_foreign_object: "#f59e0b",
  base_material_foreign_object: "#6b7280",
  anomaly: "#dc2626",
}

export const DEFECT_LABELS: Record<DefectClass, string> = {
  short: "Short",
  spur: "Spur",
  spurious_copper: "Spurious Copper",
  open: "Open Circuit",
  mousebite: "Mousebite",
  hole_breakout: "Hole Breakout",
  conductor_scratch: "Conductor Scratch",
  conductor_foreign_object: "Conductor Foreign Object",
  base_material_foreign_object: "Base Material Foreign Object",
  anomaly: "Anomaly",
}
