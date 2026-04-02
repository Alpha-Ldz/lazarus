import { Rect } from "react-konva"
import type { Detection } from "@/types"
import { DEFECT_COLORS } from "@/types"

interface BoundingBoxProps {
  detection: Detection
  isSelected: boolean
  onClick: () => void
  scale: number
}

export function BoundingBox({ detection, isSelected, onClick, scale }: BoundingBoxProps) {
  const [x1, y1, x2, y2] = detection.bbox
  const color = DEFECT_COLORS[detection.class]

  return (
    <Rect
      x={x1 * scale}
      y={y1 * scale}
      width={(x2 - x1) * scale}
      height={(y2 - y1) * scale}
      stroke={color}
      strokeWidth={isSelected ? 3 : 2}
      fill={isSelected ? `${color}33` : `${color}1A`}
      cornerRadius={2}
      onClick={onClick}
      onTap={onClick}
      style={{ cursor: "pointer" }}
    />
  )
}
