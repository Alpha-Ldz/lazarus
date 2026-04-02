import { AlertTriangle, Wrench, DollarSign, Star } from "lucide-react"
import type { Detection, RepairSheet } from "@/types"
import { DEFECT_COLORS, DEFECT_LABELS } from "@/types"
import { cn } from "@/lib/utils"

interface DiagnosticPanelProps {
  selectedDetection: Detection | null
  repairSheet: RepairSheet | null
  isLoading: boolean
}

function SeverityBadge({ severity }: { severity: RepairSheet["severity"] }) {
  const colors = {
    low: "bg-green-100 text-green-800",
    medium: "bg-yellow-100 text-yellow-800",
    high: "bg-red-100 text-red-800",
  }

  return (
    <span className={cn("px-2 py-1 rounded-full text-xs font-medium", colors[severity])}>
      {severity.charAt(0).toUpperCase() + severity.slice(1)}
    </span>
  )
}

function DifficultyStars({ difficulty }: { difficulty: number }) {
  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((star) => (
        <Star
          key={star}
          className={cn(
            "w-4 h-4",
            star <= difficulty ? "fill-yellow-400 text-yellow-400" : "text-gray-300"
          )}
        />
      ))}
    </div>
  )
}

export function DiagnosticPanel({
  selectedDetection,
  repairSheet,
  isLoading,
}: DiagnosticPanelProps) {
  if (!selectedDetection) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-gray-500 text-sm p-4">
        <AlertTriangle className="w-12 h-12 text-gray-300 mb-3" />
        <p className="text-center">Click on a detection to see repair details</p>
      </div>
    )
  }

  const defectColor = DEFECT_COLORS[selectedDetection.class_name]
  const defectLabel = DEFECT_LABELS[selectedDetection.class_name]

  return (
    <div className="h-full flex flex-col gap-4 overflow-y-auto">
      {/* Detection Info */}
      <div className="bg-gray-50 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <div
            className="w-4 h-4 rounded"
            style={{ backgroundColor: defectColor }}
          />
          <h3 className="font-semibold text-gray-900">{defectLabel}</h3>
        </div>
        <p className="text-sm text-gray-600">
          Confidence: {(selectedDetection.confidence * 100).toFixed(1)}%
        </p>
        <p className="text-xs text-gray-500 mt-1">
          Position: ({selectedDetection.bbox[0]}, {selectedDetection.bbox[1]}) to ({selectedDetection.bbox[2]}, {selectedDetection.bbox[3]})
        </p>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex-1 flex flex-col items-center justify-center gap-3">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-gray-600">Generating repair sheet...</p>
        </div>
      )}

      {/* Repair Sheet */}
      {repairSheet && !isLoading && (
        <div className="flex-1 flex flex-col gap-4">
          {/* Component & Severity */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide">Component</p>
              <p className="font-semibold text-gray-900">{repairSheet.component}</p>
            </div>
            <SeverityBadge severity={repairSheet.severity} />
          </div>

          {/* Cost & Difficulty */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="flex items-center gap-2 text-gray-500 mb-1">
                <DollarSign className="w-4 h-4" />
                <span className="text-xs uppercase tracking-wide">Est. Cost</span>
              </div>
              <p className="font-semibold text-gray-900">{repairSheet.estimated_cost}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="flex items-center gap-2 text-gray-500 mb-1">
                <Wrench className="w-4 h-4" />
                <span className="text-xs uppercase tracking-wide">Difficulty</span>
              </div>
              <DifficultyStars difficulty={repairSheet.difficulty} />
            </div>
          </div>

          {/* Repair Steps */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">Repair Steps</h4>
            <ol className="space-y-2">
              {repairSheet.steps.map((step, index) => (
                <li key={index} className="flex gap-3 text-sm">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-medium">
                    {index + 1}
                  </span>
                  <span className="text-gray-700 pt-0.5">{step}</span>
                </li>
              ))}
            </ol>
          </div>
        </div>
      )}
    </div>
  )
}
