import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Zap, 
  Settings, 
  Play, 
  Pause, 
  CheckCircle, 
  AlertCircle,
  Clock,
  FileText,
  Brain,
  Building2,
  Sparkles,
  TrendingUp,
  Eye,
  EyeOff,
  Trash2,
  RefreshCw,
  ArrowRight,
  Info
} from 'lucide-react'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useProcessDocuments, useBatchStatus, useStopProcessing } from '../hooks/useApi'
import { useProcessingProgress, useWorkflowState } from '../hooks/useUtils'
import { useAppStore } from '../store'
import { ProcessingStatus } from '../types'

const Process: React.FC = () => {
  const uploadedFiles = useAppStore(state => state.uploadedFiles)
  const processingConfig = useAppStore(state => state.processingConfig)
  const setProcessingConfig = useAppStore(state => state.setProcessingConfig)
  const currentBatch = useAppStore(state => state.currentBatch)
  const isProcessing = useAppStore(state => state.isProcessing)
  const setIsProcessing = useAppStore(state => state.setIsProcessing)
  
  const [currentFileIndex, setCurrentFileIndex] = useState(0)
  const [estimatedTimeRemaining, setEstimatedTimeRemaining] = useState(0)
  const [processingStartTime, setProcessingStartTime] = useState<Date | null>(null)
  
  const { hasUploadedFiles } = useWorkflowState()
  const processDocumentsMutation = useProcessDocuments()
  const stopProcessingMutation = useStopProcessing()
  
  // Poll batch status when processing
  const { data: batchStatus } = useBatchStatus(
    currentBatch?.id, 
    isProcessing && !!currentBatch?.id
  )
  
  const processingStats = useProcessingProgress()

  // Update processing state based on batch status
  useEffect(() => {
    if (batchStatus) {
      if (batchStatus.status === 'completed' || batchStatus.status === 'error') {
        setIsProcessing(false)
        setProcessingStartTime(null)
        if (batchStatus.status === 'completed') {
          toast.success('All documents processed successfully!')
        }
      }
    }
  }, [batchStatus, setIsProcessing])

  // Calculate estimated time remaining
  useEffect(() => {
    if (isProcessing && processingStartTime && currentBatch) {
      const elapsed = (Date.now() - processingStartTime.getTime()) / 1000
      const avgTimePerDoc = elapsed / Math.max(1, currentBatch.processed_documents)
      const remaining = avgTimePerDoc * (currentBatch.total_documents - currentBatch.processed_documents)
      setEstimatedTimeRemaining(Math.max(0, remaining))
    }
  }, [isProcessing, processingStartTime, currentBatch])

  const handleStartProcessing = async () => {
    if (uploadedFiles.length === 0) {
      toast.error('Please upload documents first')
      return
    }

    if (!processingConfig.enable_azure && !processingConfig.enable_gemini) {
      toast.error('Please enable at least one processing service')
      return
    }

    try {
      setProcessingStartTime(new Date())
      setCurrentFileIndex(0)
      
      await processDocumentsMutation.mutateAsync({
        fileIds: uploadedFiles.map(f => f.id),
        config: processingConfig
      })
      
      toast.success('Processing started successfully')
    } catch (error) {
      setProcessingStartTime(null)
      toast.error('Failed to start processing')
    }
  }

  const handleStopProcessing = async () => {
    if (!currentBatch?.id) return
    
    if (window.confirm('Are you sure you want to stop processing? This will cancel the current batch.')) {
      try {
        await stopProcessingMutation.mutateAsync(currentBatch.id)
        setProcessingStartTime(null)
        toast.success('Processing stopped')
      } catch (error) {
        toast.error('Failed to stop processing')
      }
    }
  }

  const formatTimeRemaining = (seconds: number) => {
    if (seconds < 60) return `${Math.round(seconds)}s`
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = Math.round(seconds % 60)
    return `${minutes}m ${remainingSeconds}s`
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const getFileStatus = (index: number) => {
    if (!currentBatch) return 'pending'
    if (index < currentBatch.processed_documents) return 'completed'
    if (index === currentBatch.processed_documents && isProcessing) return 'processing'
    return 'pending'
  }

  const getFileStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-success-500" />
      case 'processing':
        return <RefreshCw className="h-5 w-5 text-primary-500 animate-spin" />
      case 'error':
        return <AlertCircle className="h-5 w-5 text-error-500" />
      default:
        return <Clock className="h-5 w-5 text-gray-400" />
    }
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <motion.h1 
          className="text-3xl font-bold text-gray-900 mb-2"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          Process Documents
        </motion.h1>
        <motion.p 
          className="text-lg text-gray-600"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          Configure and run AI-powered document analysis
        </motion.p>
      </div>

      {/* Processing Configuration */}
      <motion.div 
        className="card mb-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
      >
        <div className="card-header">
          <div className="flex items-center">
            <Settings className="h-5 w-5 text-gray-600 mr-2" />
            <h3 className="text-lg font-semibold text-gray-900">Processing Configuration</h3>
          </div>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* AI Services */}
            <div>
              <h4 className="font-medium text-gray-900 mb-3">AI Services</h4>
              <div className="space-y-3">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={processingConfig.enable_azure}
                    onChange={(e) => setProcessingConfig({ 
                      ...processingConfig, 
                      enable_azure: e.target.checked 
                    })}
                    disabled={isProcessing}
                    className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <div className="ml-3">
                    <div className="flex items-center">
                      <Building2 className="h-4 w-4 text-blue-600 mr-1" />
                      <span className="text-sm font-medium text-gray-900">Azure Document Intelligence</span>
                    </div>
                    <p className="text-xs text-gray-600">OCR and structured data extraction</p>
                  </div>
                </label>
                
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={processingConfig.enable_gemini}
                    onChange={(e) => setProcessingConfig({ 
                      ...processingConfig, 
                      enable_gemini: e.target.checked 
                    })}
                    disabled={isProcessing}
                    className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <div className="ml-3">
                    <div className="flex items-center">
                      <Sparkles className="h-4 w-4 text-purple-600 mr-1" />
                      <span className="text-sm font-medium text-gray-900">Gemini AI Analysis</span>
                    </div>
                    <p className="text-xs text-gray-600">Comprehensive document analysis</p>
                  </div>
                </label>
              </div>
            </div>

            {/* PII Handling */}
            <div>
              <h4 className="font-medium text-gray-900 mb-3">PII Handling</h4>
              <div className="space-y-2">
                {[
                  { value: 'ignore', label: 'Ignore', icon: Eye, desc: 'Keep all data as-is' },
                  { value: 'mask', label: 'Mask', icon: EyeOff, desc: 'Hide sensitive information' },
                  { value: 'remove', label: 'Remove', icon: Trash2, desc: 'Remove PII completely' }
                ].map(option => {
                  const Icon = option.icon
                  return (
                    <label key={option.value} className="flex items-center">
                      <input
                        type="radio"
                        name="pii_mode"
                        value={option.value}
                        checked={processingConfig.pii_mode === option.value}
                        onChange={(e) => setProcessingConfig({ 
                          ...processingConfig, 
                          pii_mode: e.target.value as any 
                        })}
                        disabled={isProcessing}
                        className="border-gray-300 text-primary-600 focus:ring-primary-500"
                      />
                      <div className="ml-3">
                        <div className="flex items-center">
                          <Icon className="h-4 w-4 text-gray-500 mr-1" />
                          <span className="text-sm font-medium text-gray-900">{option.label}</span>
                        </div>
                        <p className="text-xs text-gray-600">{option.desc}</p>
                      </div>
                    </label>
                  )
                })}
              </div>
            </div>

            {/* Processing Summary */}
            <div>
              <h4 className="font-medium text-gray-900 mb-3">Processing Summary</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Documents:</span>
                  <span className="font-medium">{uploadedFiles.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Azure Enabled:</span>
                  <span className={processingConfig.enable_azure ? 'text-success-600' : 'text-gray-400'}>
                    {processingConfig.enable_azure ? 'Yes' : 'No'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Gemini Enabled:</span>
                  <span className={processingConfig.enable_gemini ? 'text-success-600' : 'text-gray-400'}>
                    {processingConfig.enable_gemini ? 'Yes' : 'No'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">PII Mode:</span>
                  <span className="font-medium capitalize">{processingConfig.pii_mode}</span>
                </div>
                {estimatedTimeRemaining > 0 && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Est. Time:</span>
                    <span className="font-medium">{formatTimeRemaining(estimatedTimeRemaining)}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Document List */}
      {uploadedFiles.length > 0 && (
        <motion.div 
          className="card mb-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
        >
          <div className="card-header">
            <h3 className="text-lg font-semibold text-gray-900">
              Documents Ready for Processing ({uploadedFiles.length})
            </h3>
          </div>
          <div className="card-body p-0">
            <div className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
              {uploadedFiles.map((file, index) => {
                const status = getFileStatus(index)
                return (
                  <div key={file.id} className="flex items-center justify-between p-4 hover:bg-gray-50 transition-colors">
                    <div className="flex items-center flex-1">
                      <div className="flex-shrink-0 mr-3">
                        <FileText className="h-5 w-5 text-red-500" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">{file.filename}</p>
                        <div className="flex items-center text-xs text-gray-500 mt-1 gap-2">
                          <span>{formatFileSize(file.size)}</span>
                          <span>•</span>
                          <span>{file.content_type.split('/')[1].toUpperCase()}</span>
                          {status === 'processing' && (
                            <>
                              <span>•</span>
                              <span className="text-primary-600 font-medium">Processing...</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      {getFileStatusIcon(status)}
                      {status === 'completed' && (
                        <span className="text-xs text-success-600 font-medium">Done</span>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </motion.div>
      )}

      {/* Processing Controls */}
      <motion.div 
        className="card mb-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.4 }}
      >
        <div className="card-body">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-1">Processing Control</h3>
              <p className="text-sm text-gray-600">
                {isProcessing 
                  ? 'Processing documents with your selected AI services...'
                  : 'Start processing to analyze all uploaded documents with your selected AI services'
                }
              </p>
            </div>
            <div className="flex space-x-3">
              {!isProcessing ? (
                <button
                  onClick={handleStartProcessing}
                  disabled={
                    uploadedFiles.length === 0 || 
                    (!processingConfig.enable_azure && !processingConfig.enable_gemini) ||
                    processDocumentsMutation.isLoading
                  }
                  className="btn btn-primary btn-lg"
                >
                  {processDocumentsMutation.isLoading ? (
                    <RefreshCw className="h-5 w-5 mr-2 animate-spin" />
                  ) : (
                    <Play className="h-5 w-5 mr-2" />
                  )}
                  Start Processing
                </button>
              ) : (
                <button
                  onClick={handleStopProcessing}
                  disabled={stopProcessingMutation.isLoading}
                  className="btn btn-error btn-lg"
                >
                  {stopProcessingMutation.isLoading ? (
                    <RefreshCw className="h-5 w-5 mr-2 animate-spin" />
                  ) : (
                    <Pause className="h-5 w-5 mr-2" />
                  )}
                  Stop Processing
                </button>
              )}
            </div>
          </div>
        </div>
      </motion.div>

      {/* Processing Progress */}
      <AnimatePresence>
        {(isProcessing || processingStats.progress > 0) && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
            className="card mb-6"
          >
            <div className="card-header">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">Processing Progress</h3>
                <div className="text-sm text-gray-600">
                  {processingStats.completed} of {processingStats.total} completed
                </div>
              </div>
            </div>
            <div className="card-body">
              {/* Progress Bar */}
              <div className="progress-bar mb-4">
                <motion.div
                  className="progress-fill"
                  initial={{ width: 0 }}
                  animate={{ width: `${processingStats.progress}%` }}
                  transition={{ duration: 0.3 }}
                />
              </div>

              {/* Progress Stats */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
                <div className="flex items-center">
                  <TrendingUp className="h-5 w-5 text-blue-500 mr-2" />
                  <div>
                    <p className="text-sm text-gray-600">Progress</p>
                    <p className="font-semibold text-gray-900">{processingStats.progress}%</p>
                  </div>
                </div>
                <div className="flex items-center">
                  <CheckCircle className="h-5 w-5 text-success-500 mr-2" />
                  <div>
                    <p className="text-sm text-gray-600">Completed</p>
                    <p className="font-semibold text-gray-900">{processingStats.completed}</p>
                  </div>
                </div>
                <div className="flex items-center">
                  <AlertCircle className="h-5 w-5 text-error-500 mr-2" />
                  <div>
                    <p className="text-sm text-gray-600">Failed</p>
                    <p className="font-semibold text-gray-900">{processingStats.failed}</p>
                  </div>
                </div>
                <div className="flex items-center">
                  <Clock className="h-5 w-5 text-warning-500 mr-2" />
                  <div>
                    <p className="text-sm text-gray-600">Est. Remaining</p>
                    <p className="font-semibold text-gray-900">
                      {estimatedTimeRemaining > 0 ? formatTimeRemaining(estimatedTimeRemaining) : '--'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Processing Status */}
              {isProcessing && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <div className="flex items-center">
                    <RefreshCw className="h-5 w-5 text-blue-600 mr-2 animate-spin" />
                    <div>
                      <h4 className="font-medium text-blue-900">Processing Active</h4>
                      <p className="text-sm text-blue-700">
                        AI services are analyzing your documents. This typically takes 20-60 seconds per document.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Completion Status */}
              {!isProcessing && processingStats.progress === 100 && (
                <div className="bg-success-50 border border-success-200 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center">
                      <CheckCircle className="h-5 w-5 text-success-600 mr-2" />
                      <div>
                        <h4 className="font-medium text-success-900">Processing Complete!</h4>
                        <p className="text-sm text-success-700">
                          All documents have been processed successfully. Review results or generate workpaper.
                        </p>
                      </div>
                    </div>
                    <div className="flex space-x-3">
                      <Link to="/results" className="btn btn-success btn-sm">
                        View Results
                        <ArrowRight className="ml-1 h-4 w-4" />
                      </Link>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* No Documents Message */}
      {!hasUploadedFiles && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.5 }}
        >
          <div className="card text-center py-12">
            <div className="card-body">
              <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No Documents to Process</h3>
              <p className="text-gray-600 mb-6">
                Upload tax documents first to begin AI-powered processing
              </p>
              <Link to="/upload" className="btn btn-primary">
                Go to Upload
                <ArrowRight className="ml-1 h-4 w-4" />
              </Link>
            </div>
          </div>
        </motion.div>
      )}

      {/* Processing Info */}
      {hasUploadedFiles && !isProcessing && processingStats.progress === 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.6 }}
          className="card bg-gradient-to-r from-primary-50 to-primary-100 border-primary-200"
        >
          <div className="card-body">
            <div className="flex items-start">
              <Info className="h-6 w-6 text-primary-600 mt-0.5 mr-3" />
              <div>
                <h3 className="text-lg font-semibold text-primary-900 mb-2">Ready to Process</h3>
                <p className="text-primary-700 mb-4">
                  Your {uploadedFiles.length} document{uploadedFiles.length !== 1 ? 's are' : ' is'} ready for AI-powered analysis. 
                  The processing will extract structured data, analyze content, and prepare professional categorization.
                </p>
                <div className="bg-white/50 rounded-lg p-4">
                  <h4 className="font-medium text-primary-900 mb-2">What happens during processing:</h4>
                  <ul className="text-sm text-primary-800 space-y-1">
                    {processingConfig.enable_azure && (
                      <li>• Azure AI extracts structured data using prebuilt tax models</li>
                    )}
                    {processingConfig.enable_gemini && (
                      <li>• Gemini AI provides comprehensive document analysis and categorization</li>
                    )}
                    <li>• Data validation and quality checks are performed</li>
                    <li>• Professional bookmark structure is generated for workpapers</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  )
}

export default Process
