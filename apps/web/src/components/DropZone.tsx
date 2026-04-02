import { useCallback } from "react"
import { useDropzone } from "react-dropzone"
import { Upload, Image, AlertCircle } from "lucide-react"
import { cn } from "@/lib/utils"

interface DropZoneProps {
  onFileAccepted: (file: File) => void
  isLoading?: boolean
  currentFile?: File | null
}

export function DropZone({ onFileAccepted, isLoading, currentFile }: DropZoneProps) {
  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length > 0) {
        onFileAccepted(acceptedFiles[0])
      }
    },
    [onFileAccepted]
  )

  const { getRootProps, getInputProps, isDragActive, fileRejections } = useDropzone({
    onDrop,
    accept: {
      "image/jpeg": [".jpg", ".jpeg"],
      "image/png": [".png"],
    },
    maxFiles: 1,
    disabled: isLoading,
  })

  const hasError = fileRejections.length > 0

  return (
    <div className="flex flex-col gap-3">
      <div
        {...getRootProps()}
        className={cn(
          "border-2 border-dashed rounded-lg p-6 flex flex-col items-center justify-center gap-3 cursor-pointer transition-colors min-h-[200px]",
          isDragActive && "border-blue-500 bg-blue-50",
          hasError && "border-red-500 bg-red-50",
          isLoading && "opacity-50 cursor-not-allowed",
          !isDragActive && !hasError && "border-gray-300 hover:border-gray-400 hover:bg-gray-50"
        )}
      >
        <input {...getInputProps()} />

        {isLoading ? (
          <>
            <div className="w-10 h-10 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-gray-600 text-center">Analyzing...</p>
          </>
        ) : isDragActive ? (
          <>
            <Upload className="w-10 h-10 text-blue-500" />
            <p className="text-sm text-blue-600 text-center font-medium">Drop your PCB image here</p>
          </>
        ) : (
          <>
            <Image className="w-10 h-10 text-gray-400" />
            <div className="text-center">
              <p className="text-sm text-gray-600">
                <span className="font-medium text-blue-600">Click to upload</span> or drag and drop
              </p>
              <p className="text-xs text-gray-500 mt-1">JPG or PNG</p>
            </div>
          </>
        )}
      </div>

      {hasError && (
        <div className="flex items-center gap-2 text-red-600 text-sm">
          <AlertCircle className="w-4 h-4" />
          <span>Please upload a valid JPG or PNG image</span>
        </div>
      )}

      {currentFile && !isLoading && (
        <div className="flex items-center gap-2 text-gray-600 text-sm bg-gray-100 rounded-lg px-3 py-2">
          <Image className="w-4 h-4" />
          <span className="truncate flex-1">{currentFile.name}</span>
        </div>
      )}
    </div>
  )
}
