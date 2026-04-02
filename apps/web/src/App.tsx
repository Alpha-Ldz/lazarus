import { useState, useCallback } from "react"
import { AlertCircle } from "lucide-react"
import type { Detection } from "@/types"
import { DropZone } from "@/components/DropZone"
import { PCBViewer } from "@/components/PCBViewer"
import { DiagnosticPanel } from "@/components/DiagnosticPanel"
import { ExportButton } from "@/components/ExportButton"
import { useAnalyze } from "@/hooks/useAnalyze"

function App() {
  const [currentFile, setCurrentFile] = useState<File | null>(null)
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [selectedDetection, setSelectedDetection] = useState<Detection | null>(null)

  const {
    isAnalyzing,
    isDiagnosing,
    error,
    detections,
    imageSize,
    repairSheet,
    analyze,
    diagnose,
  } = useAnalyze()

  const handleFileAccepted = useCallback(
    async (file: File) => {
      setCurrentFile(file)
      setSelectedDetection(null)

      // Create object URL for preview
      const url = URL.createObjectURL(file)
      setImageUrl(url)

      // Analyze the image
      await analyze(file)
    },
    [analyze]
  )

  const handleDetectionSelect = useCallback(
    async (detection: Detection) => {
      setSelectedDetection(detection)
      await diagnose(detection)
    },
    [diagnose]
  )

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4 shrink-0">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
            <span className="text-2xl">🔬</span> Lazarus
          </h1>
          {detections.length > 0 && (
            <div className="text-sm text-gray-600">
              {detections.length} defect{detections.length > 1 ? "s" : ""} detected
            </div>
          )}
        </div>
      </header>

      {/* Error Banner */}
      {error && (
        <div className="bg-red-50 border-b border-red-200 px-6 py-3 flex items-center gap-2 text-red-700">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span className="text-sm">{error}</span>
        </div>
      )}

      {/* Main content - 3 columns */}
      <main className="flex-1 flex overflow-hidden">
        {/* Left column - Drop Zone */}
        <div className="w-64 border-r border-gray-200 bg-white p-4 flex flex-col shrink-0">
          <h2 className="text-sm font-medium text-gray-700 mb-3">Upload PCB</h2>
          <DropZone
            onFileAccepted={handleFileAccepted}
            isLoading={isAnalyzing}
            currentFile={currentFile}
          />

          {/* Detection Legend */}
          {detections.length > 0 && (
            <div className="mt-4 pt-4 border-t border-gray-200">
              <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                Detections
              </h3>
              <div className="space-y-1">
                {detections.map((detection, index) => (
                  <button
                    key={index}
                    onClick={() => handleDetectionSelect(detection)}
                    className={`w-full text-left px-2 py-1.5 rounded text-sm transition-colors ${
                      selectedDetection === detection
                        ? "bg-blue-50 text-blue-700"
                        : "hover:bg-gray-50 text-gray-700"
                    }`}
                  >
                    <span className="font-medium">{detection.class_name}</span>
                    <span className="text-gray-500 ml-1">
                      ({(detection.confidence * 100).toFixed(0)}%)
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Center column - PCB Viewer */}
        <div className="flex-1 bg-gray-100 flex items-center justify-center overflow-hidden">
          {imageUrl && imageSize ? (
            <PCBViewer
              imageSrc={imageUrl}
              imageSize={imageSize}
              detections={detections}
              selectedDetection={selectedDetection}
              onDetectionSelect={handleDetectionSelect}
            />
          ) : (
            <div className="text-gray-500 text-sm text-center p-4">
              <p>Upload a PCB image to start analysis</p>
              <p className="text-xs text-gray-400 mt-1">
                Supports JPG and PNG formats
              </p>
            </div>
          )}
        </div>

        {/* Right column - Diagnostic Panel */}
        <div className="w-80 border-l border-gray-200 bg-white p-4 flex flex-col shrink-0">
          <h2 className="text-sm font-medium text-gray-700 mb-3">Diagnostic</h2>
          <div className="flex-1 overflow-hidden">
            <DiagnosticPanel
              selectedDetection={selectedDetection}
              repairSheet={repairSheet}
              isLoading={isDiagnosing}
            />
          </div>

          {/* Export Button */}
          {selectedDetection && repairSheet && (
            <div className="pt-4 mt-4 border-t border-gray-200">
              <ExportButton
                detection={selectedDetection}
                repairSheet={repairSheet}
                disabled={isDiagnosing}
              />
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

export default App
