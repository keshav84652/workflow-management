import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  X, 
  ZoomIn, 
  ZoomOut, 
  RotateCw, 
  Download, 
  Eye,
  EyeOff,
  RefreshCw,
  Image as ImageIcon
} from 'lucide-react'
import { useDocumentVisualization } from '../hooks/useApi'
import toast from 'react-hot-toast'

interface DocumentVisualizationProps {
  documentId: string
  filename: string
  isOpen: boolean
  onClose: () => void
  visualizationType?: 'box' | 'tick'
}

const DocumentVisualization: React.FC<DocumentVisualizationProps> = ({
  documentId,
  filename,
  isOpen,
  onClose,
  visualizationType = 'box'
}) => {
  const [zoom, setZoom] = useState(1)
  const [rotation, setRotation] = useState(0)
  const [showAnnotations, setShowAnnotations] = useState(true)
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  
  const visualizationMutation = useDocumentVisualization()

  React.useEffect(() => {
    if (isOpen && !imageUrl) {
      loadVisualization()
    }
  }, [isOpen, visualizationType])

  const loadVisualization = async () => {
    try {
      const imageBlob = await visualizationMutation.mutateAsync({ 
        documentId, 
        visualizationType 
      })
      const url = URL.createObjectURL(imageBlob)
      setImageUrl(url)
    } catch (error) {
      console.error('Visualization failed:', error)
      toast.error('Failed to load document visualization')
    }
  }

  const handleClose = () => {
    if (imageUrl) {
      URL.revokeObjectURL(imageUrl)
      setImageUrl(null)
    }
    setZoom(1)
    setRotation(0)
    onClose()
  }

  const handleZoomIn = () => setZoom(prev => Math.min(prev * 1.2, 3))
  const handleZoomOut = () => setZoom(prev => Math.max(prev / 1.2, 0.5))
  const handleRotate = () => setRotation(prev => (prev + 90) % 360)

  const handleDownload = () => {
    if (imageUrl) {
      const link = document.createElement('a')
      link.href = imageUrl
      link.download = `${filename}_visualization_${visualizationType}.png`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      toast.success('Visualization downloaded')
    }
  }

  if (!isOpen) return null

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75"
        onClick={handleClose}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          className="relative bg-white rounded-lg shadow-xl max-w-6xl max-h-[90vh] w-full mx-4 flex flex-col"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">{filename}</h3>
              <p className="text-sm text-gray-600">
                Document Visualization ({visualizationType === 'box' ? 'Box Annotations' : 'Tick Marks'})
              </p>
            </div>
            <div className="flex items-center space-x-2">
              {/* Controls */}
              <button
                onClick={handleZoomOut}
                className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
                title="Zoom Out"
              >
                <ZoomOut className="h-4 w-4" />
              </button>
              <span className="text-sm text-gray-600 min-w-[60px] text-center">
                {Math.round(zoom * 100)}%
              </span>
              <button
                onClick={handleZoomIn}
                className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
                title="Zoom In"
              >
                <ZoomIn className="h-4 w-4" />
              </button>
              <button
                onClick={handleRotate}
                className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
                title="Rotate"
              >
                <RotateCw className="h-4 w-4" />
              </button>
              <button
                onClick={() => setShowAnnotations(!showAnnotations)}
                className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
                title={showAnnotations ? 'Hide Annotations' : 'Show Annotations'}
              >
                {showAnnotations ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
              <button
                onClick={handleDownload}
                disabled={!imageUrl}
                className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded disabled:opacity-50"
                title="Download"
              >
                <Download className="h-4 w-4" />
              </button>
              <button
                onClick={loadVisualization}
                disabled={visualizationMutation.isLoading}
                className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded disabled:opacity-50"
                title="Refresh"
              >
                {visualizationMutation.isLoading ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4" />
                )}
              </button>
              <button
                onClick={handleClose}
                className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
                title="Close"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Image Container */}
          <div className="flex-1 overflow-auto bg-gray-50 p-4">
            {visualizationMutation.isLoading ? (
              <div className="flex items-center justify-center h-64">
                <div className="text-center">
                  <RefreshCw className="h-8 w-8 text-gray-400 mx-auto mb-2 animate-spin" />
                  <p className="text-gray-600">Loading visualization...</p>
                </div>
              </div>
            ) : imageUrl ? (
              <div className="flex items-center justify-center min-h-full">
                <img
                  src={imageUrl}
                  alt={`${filename} visualization`}
                  className="max-w-none transition-transform duration-200"
                  style={{
                    transform: `scale(${zoom}) rotate(${rotation}deg)`,
                    opacity: showAnnotations ? 1 : 0.7
                  }}
                />
              </div>
            ) : (
              <div className="flex items-center justify-center h-64">
                <div className="text-center">
                  <ImageIcon className="h-8 w-8 text-gray-400 mx-auto mb-2" />
                  <p className="text-gray-600">Failed to load visualization</p>
                  <button
                    onClick={loadVisualization}
                    className="btn btn-secondary btn-sm mt-2"
                  >
                    Try Again
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-gray-200 bg-gray-50">
            <div className="flex items-center justify-between text-sm text-gray-600">
              <div className="flex items-center space-x-4">
                <span>Visualization Type: {visualizationType === 'box' ? 'Box Annotations' : 'Tick Marks'}</span>
                <span>•</span>
                <span>Zoom: {Math.round(zoom * 100)}%</span>
                <span>•</span>
                <span>Rotation: {rotation}°</span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-xs">Use mouse wheel to zoom, drag to pan</span>
              </div>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

export default DocumentVisualization