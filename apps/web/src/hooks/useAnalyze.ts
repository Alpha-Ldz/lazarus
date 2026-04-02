import { useState, useCallback } from "react"
import type { Detection, AnalyzeResponse, RepairSheet, DiagnoseResponse } from "@/types"
import { config } from "@/config"

interface UseAnalyzeResult {
  isAnalyzing: boolean
  isDiagnosing: boolean
  error: string | null
  detections: Detection[]
  imageSize: { width: number; height: number } | null
  repairSheet: RepairSheet | null
  analyze: (file: File) => Promise<void>
  diagnose: (detection: Detection) => Promise<void>
  reset: () => void
}

export function useAnalyze(): UseAnalyzeResult {
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [isDiagnosing, setIsDiagnosing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [detections, setDetections] = useState<Detection[]>([])
  const [imageSize, setImageSize] = useState<{ width: number; height: number } | null>(null)
  const [repairSheet, setRepairSheet] = useState<RepairSheet | null>(null)

  const analyze = useCallback(async (file: File) => {
    setIsAnalyzing(true)
    setError(null)
    setDetections([])
    setImageSize(null)
    setRepairSheet(null)

    try {
      // Get image dimensions from file
      const img = new Image()
      const imageUrl = URL.createObjectURL(file)
      await new Promise<void>((resolve, reject) => {
        img.onload = () => {
          setImageSize({ width: img.naturalWidth, height: img.naturalHeight })
          resolve()
        }
        img.onerror = reject
        img.src = imageUrl
      })

      const formData = new FormData()
      formData.append("file", file)

      const response = await fetch(`${config.apiBaseUrl}/api/analyze`, {
        method: "POST",
        body: formData,
      })

      if (!response.ok) {
        throw new Error(`Analysis failed: ${response.statusText}`)
      }

      const data: AnalyzeResponse = await response.json()
      setDetections(data.detections)
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred during analysis")
    } finally {
      setIsAnalyzing(false)
    }
  }, [])

  const diagnose = useCallback(async (detection: Detection) => {
    setIsDiagnosing(true)
    setError(null)

    try {
      const response = await fetch(`${config.apiBaseUrl}/api/diagnose`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ detections: [detection] }),
      })

      if (!response.ok) {
        throw new Error(`Diagnosis failed: ${response.statusText}`)
      }

      const data: DiagnoseResponse = await response.json()
      setRepairSheet(data.repair_sheet)
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred during diagnosis")
    } finally {
      setIsDiagnosing(false)
    }
  }, [])

  const reset = useCallback(() => {
    setIsAnalyzing(false)
    setIsDiagnosing(false)
    setError(null)
    setDetections([])
    setImageSize(null)
    setRepairSheet(null)
  }, [])

  return {
    isAnalyzing,
    isDiagnosing,
    error,
    detections,
    imageSize,
    repairSheet,
    analyze,
    diagnose,
    reset,
  }
}
