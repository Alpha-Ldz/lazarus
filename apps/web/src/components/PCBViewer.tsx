import { useEffect, useRef, useState } from "react"
import { Stage, Layer, Image as KonvaImage } from "react-konva"
import type { Detection } from "@/types"
import { BoundingBox } from "./BoundingBox"

interface PCBViewerProps {
  imageSrc: string
  imageSize: { width: number; height: number }
  detections: Detection[]
  selectedDetection: Detection | null
  onDetectionSelect: (detection: Detection) => void
}

export function PCBViewer({
  imageSrc,
  imageSize,
  detections,
  selectedDetection,
  onDetectionSelect,
}: PCBViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 })
  const [image, setImage] = useState<HTMLImageElement | null>(null)

  useEffect(() => {
    const img = new window.Image()
    img.src = imageSrc
    img.onload = () => {
      setImage(img)
    }
  }, [imageSrc])

  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect()
        setDimensions({
          width: rect.width,
          height: rect.height,
        })
      }
    }

    updateDimensions()
    window.addEventListener("resize", updateDimensions)
    return () => window.removeEventListener("resize", updateDimensions)
  }, [])

  const scale = Math.min(
    dimensions.width / imageSize.width,
    dimensions.height / imageSize.height
  )

  const scaledWidth = imageSize.width * scale
  const scaledHeight = imageSize.height * scale
  const offsetX = (dimensions.width - scaledWidth) / 2
  const offsetY = (dimensions.height - scaledHeight) / 2

  return (
    <div ref={containerRef} className="w-full h-full">
      <Stage width={dimensions.width} height={dimensions.height}>
        <Layer x={offsetX} y={offsetY}>
          {image && (
            <KonvaImage
              image={image}
              width={scaledWidth}
              height={scaledHeight}
            />
          )}
          {detections.map((detection, index) => (
            <BoundingBox
              key={index}
              detection={detection}
              isSelected={selectedDetection === detection}
              onClick={() => onDetectionSelect(detection)}
              scale={scale}
            />
          ))}
        </Layer>
      </Stage>
    </div>
  )
}
