export type DefectClass =
  | "open"
  | "short"
  | "mousebite"
  | "spur"
  | "copper"
  | "pin-hole"

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
  open: "#ef4444",
  short: "#f97316",
  mousebite: "#eab308",
  spur: "#3b82f6",
  copper: "#8b5cf6",
  "pin-hole": "#6b7280",
}

export const DEFECT_LABELS: Record<DefectClass, string> = {
  open: "Open Circuit",
  short: "Short",
  mousebite: "Mousebite",
  spur: "Spur",
  copper: "Spurious Copper",
  "pin-hole": "Pin Hole",
}
