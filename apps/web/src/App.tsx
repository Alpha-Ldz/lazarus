import { useState } from "react"
import type { Detection, RepairSheet } from "@/types"

function App() {
  const [image, setImage] = useState<string | null>(null)
  const [detections, setDetections] = useState<Detection[]>([])
  const [imageSize, setImageSize] = useState<{ width: number; height: number } | null>(null)
  const [selectedDetection, setSelectedDetection] = useState<Detection | null>(null)
  const [repairSheet, setRepairSheet] = useState<RepairSheet | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)

  // Placeholder - will be replaced with actual components
  console.log({ image, detections, imageSize, selectedDetection, repairSheet, isAnalyzing })
  console.log({ setImage, setDetections, setImageSize, setSelectedDetection, setRepairSheet, setIsAnalyzing })

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4 shrink-0">
        <h1 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
          <span className="text-2xl">🔬</span> Lazarus
        </h1>
      </header>

      {/* Main content - 3 columns */}
      <main className="flex-1 flex overflow-hidden">
        {/* Left column - Drop Zone */}
        <div className="w-64 border-r border-gray-200 bg-white p-4 flex flex-col">
          <h2 className="text-sm font-medium text-gray-700 mb-3">Upload PCB</h2>
          <div className="flex-1 border-2 border-dashed border-gray-300 rounded-lg flex items-center justify-center text-gray-500 text-sm text-center p-4">
            Drag your PCB image here
          </div>
        </div>

        {/* Center column - PCB Viewer */}
        <div className="flex-1 bg-gray-100 p-4 flex items-center justify-center">
          <div className="text-gray-500 text-sm">
            Upload an image to start analysis
          </div>
        </div>

        {/* Right column - Diagnostic Panel */}
        <div className="w-80 border-l border-gray-200 bg-white p-4 flex flex-col">
          <h2 className="text-sm font-medium text-gray-700 mb-3">Diagnostic</h2>
          <div className="flex-1 flex items-center justify-center text-gray-500 text-sm">
            Select a detection to see details
          </div>
        </div>
      </main>
    </div>
  )
}

export default App
