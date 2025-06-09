import React, { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Upload as UploadIcon,
  File,
  X,
  CheckCircle,
  AlertCircle,
  FileText,
  Image,
  Trash2,
  Info,
  Plus,
  RefreshCw,
  ArrowRight,
  Sparkles
} from 'lucide-react'
import toast from 'react-hot-toast'
import { Link } from 'react-router-dom'
import { useUploadFiles, useDeleteFile, useClearAllFiles } from '../hooks/useApi'
import { useFileValidation, useUploadProgress, useWorkflowState } from '../hooks/useUtils'
import { useAppStore } from '../store'
import { FILE_UPLOAD } from '../utils/constants'
import { generateMockFileUpload, DEMO_FILES } from '../utils/demoData'

const Upload: React.FC = () => {
  const uploadedFiles = useAppStore(state => state.uploadedFiles)
  const addUploadedFiles = useAppStore(state => state.addUploadedFiles)
  const removeUploadedFile = useAppStore(state => state.removeUploadedFile)
  const [draggedFileId, setDraggedFileId] = useState<string | null>(null)
  
  const { validateFiles } = useFileValidation()
  const { progress, isUploading, uploadedCount, totalCount, startUpload, updateProgress, finishUpload, resetUpload } = useUploadProgress()
  const { hasUploadedFiles } = useWorkflowState()
  
  const uploadFilesMutation = useUploadFiles()
  const deleteFileMutation = useDeleteFile()
  const clearAllFilesMutation = useClearAllFiles()

  const onDrop = useCallback(async (acceptedFiles: File[], rejectedFiles: any[]) => {
    // Handle rejected files
    if (rejectedFiles.length > 0) {
      rejectedFiles.forEach(({ file, errors }) => {
        errors.forEach((error: any) => {
          if (error.code === 'file-too-large') {
            toast.error(`${file.name} is too large. Maximum size is ${FILE_UPLOAD.maxSize / 1024 / 1024}MB.`)
          } else if (error.code === 'file-invalid-type') {
            toast.error(`${file.name} is not a supported file type.`)
          } else {
            toast.error(`Error with ${file.name}: ${error.message}`)
          }
        })
      })
    }

    // Validate accepted files
    const { errors, validFiles } = validateFiles(acceptedFiles)
    
    if (errors.length > 0) {
      errors.forEach(error => toast.error(error))
    }
    
    if (validFiles.length === 0) return

    // Check total file limit including existing files
    const totalAfterUpload = uploadedFiles.length + validFiles.length
    if (totalAfterUpload > FILE_UPLOAD.maxFiles) {
      toast.error(`Cannot upload ${validFiles.length} files. Maximum ${FILE_UPLOAD.maxFiles} files allowed total.`)
      return
    }

    // Start upload process
    startUpload(validFiles.length)
    
    try {
      await uploadFilesMutation.mutateAsync(validFiles)
      finishUpload()
      toast.success(`Successfully uploaded ${validFiles.length} file(s)`)
    } catch (error) {
      resetUpload()
      toast.error('Upload failed. Please try again.')
    }
  }, [uploadedFiles.length, validateFiles, startUpload, finishUpload, resetUpload, uploadFilesMutation])

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
      'image/tiff': ['.tiff', '.tif']
    },
    maxSize: FILE_UPLOAD.maxSize,
    multiple: true,
    disabled: isUploading
  })

  const handleRemoveFile = async (fileId: string) => {
    try {
      await deleteFileMutation.mutateAsync(fileId)
      removeUploadedFile(fileId)
      toast.success('File removed')
    } catch (error) {
      toast.error('Failed to remove file')
    }
  }

  const handleClearAllFiles = async () => {
    if (uploadedFiles.length === 0) return
    
    if (window.confirm(`Are you sure you want to remove all ${uploadedFiles.length} files?`)) {
      try {
        await clearAllFilesMutation.mutateAsync()
        toast.success('All files cleared')
      } catch (error) {
        toast.error('Failed to clear files')
      }
    }
  }

  const handleLoadDemoData = () => {
    const demoFiles = DEMO_FILES.slice(0, 5).map((filename, index) =>
      generateMockFileUpload(filename, index)
    )
    addUploadedFiles(demoFiles)
    toast.success(`Loaded ${demoFiles.length} demo files for testing`, {
      icon: '🎭'
    })
  }

  const getFileIcon = (contentType: string) => {
    if (contentType === 'application/pdf') {
      return <FileText className="h-5 w-5 text-red-500" />
    }
    return <Image className="h-5 w-5 text-blue-500" />
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const getUploadZoneClass = () => {
    if (isUploading) return 'border-blue-300 bg-blue-50'
    if (isDragReject) return 'border-red-300 bg-red-50'
    if (isDragActive) return 'border-primary-300 bg-primary-50'
    return 'border-gray-300 hover:border-gray-400'
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
          Upload Tax Documents
        </motion.h1>
        <motion.p 
          className="text-lg text-gray-600"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          Upload your tax documents for AI-powered processing and analysis
        </motion.p>
        
        {/* Offline Mode Indicator */}
        <AnimatePresence>
          {uploadFilesMutation.isError && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-center"
            >
              <AlertCircle className="h-5 w-5 text-amber-600 mr-2" />
              <div>
                <p className="text-sm font-medium text-amber-800">Demo Mode Active</p>
                <p className="text-xs text-amber-700">Backend server not available. Files are stored locally for demonstration.</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Upload Instructions */}
      <motion.div 
        className="card mb-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
      >
        <div className="card-body">
          <div className="flex items-start">
            <Info className="h-5 w-5 text-blue-500 mt-0.5 mr-3 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="font-medium text-gray-900 mb-2">Supported File Types & Requirements</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-600">
                <div>
                  <ul className="space-y-1">
                    <li>• <strong>PDF files:</strong> Tax forms, statements, receipts</li>
                    <li>• <strong>Image files:</strong> JPG, PNG, TIFF formats</li>
                    <li>• <strong>Maximum file size:</strong> {FILE_UPLOAD.maxSize / 1024 / 1024}MB per file</li>
                  </ul>
                </div>
                <div>
                  <ul className="space-y-1">
                    <li>• <strong>Maximum files:</strong> {FILE_UPLOAD.maxFiles} files per batch</li>
                    <li>• <strong>Common forms:</strong> W-2, 1099-INT, 1099-DIV, 1099-G, 1098, K-1</li>
                    <li>• <strong>Current uploaded:</strong> {uploadedFiles.length} / {FILE_UPLOAD.maxFiles}</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Demo Data Section */}
      <motion.div
        className="card mb-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.25 }}
      >
        <div className="card-body">
          <div className="flex items-center justify-between">
            <div className="flex items-start">
              <Sparkles className="h-5 w-5 text-purple-500 mt-0.5 mr-3 flex-shrink-0" />
              <div>
                <h3 className="font-medium text-gray-900 mb-1">Demo Mode</h3>
                <p className="text-sm text-gray-600">
                  Load sample tax documents to test the application without uploading real files
                </p>
              </div>
            </div>
            <button
              onClick={handleLoadDemoData}
              className="btn btn-secondary btn-sm"
              disabled={uploadedFiles.length >= FILE_UPLOAD.maxFiles - 5}
            >
              <Sparkles className="h-4 w-4 mr-1" />
              Load Demo Files
            </button>
          </div>
        </div>
      </motion.div>

      {/* Drop Zone */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.3 }}
      >
        <div
          {...getRootProps()}
          className={`
            relative border-2 border-dashed rounded-lg p-8 text-center transition-all duration-200 cursor-pointer
            ${getUploadZoneClass()}
            ${isUploading ? 'pointer-events-none' : ''}
          `}
        >
          <input {...getInputProps()} />
          
          <div className="flex flex-col items-center justify-center py-8">
            {isUploading ? (
              <>
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mb-4"></div>
                <p className="text-lg font-medium text-gray-700 mb-2">
                  Uploading {uploadedCount} of {totalCount} files...
                </p>
                <div className="w-64 bg-gray-200 rounded-full h-2 mb-2">
                  <motion.div
                    className="bg-primary-600 h-2 rounded-full"
                    initial={{ width: 0 }}
                    animate={{ width: `${progress}%` }}
                    transition={{ duration: 0.3 }}
                  />
                </div>
                <p className="text-sm text-gray-500">{Math.round(progress)}% complete</p>
              </>
            ) : (
              <>
                <UploadIcon className="h-12 w-12 text-gray-400 mb-4" />
                <p className="text-lg font-medium text-gray-700 mb-2">
                  {isDragActive
                    ? isDragReject
                      ? 'Some files are not supported'
                      : 'Drop your files here'
                    : 'Drag & drop files here, or click to select'
                  }
                </p>
                <p className="text-sm text-gray-500 mb-4">
                  Support for PDF, JPG, PNG, TIFF files up to {FILE_UPLOAD.maxSize / 1024 / 1024}MB each
                </p>
                {uploadedFiles.length < FILE_UPLOAD.maxFiles && (
                  <div className="flex items-center gap-2 text-primary-600">
                    <Plus className="h-4 w-4" />
                    <span className="text-sm font-medium">
                      Add up to {FILE_UPLOAD.maxFiles - uploadedFiles.length} more files
                    </span>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </motion.div>

      {/* Uploaded Files List */}
      <AnimatePresence>
        {uploadedFiles.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
            className="mt-8"
          >
            <div className="card">
              <div className="card-header">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-gray-900">
                    Uploaded Files ({uploadedFiles.length})
                  </h3>
                  <div className="flex items-center gap-3">
                    <button
                      onClick={handleClearAllFiles}
                      disabled={clearAllFilesMutation.isLoading}
                      className="btn btn-secondary btn-sm"
                    >
                      {clearAllFilesMutation.isLoading ? (
                        <RefreshCw className="h-4 w-4 mr-1 animate-spin" />
                      ) : (
                        <Trash2 className="h-4 w-4 mr-1" />
                      )}
                      Clear All
                    </button>
                  </div>
                </div>
              </div>
              <div className="card-body p-0">
                <div className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
                  {uploadedFiles.map((file, index) => (
                    <motion.div
                      key={file.id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 20 }}
                      transition={{ duration: 0.2, delay: index * 0.05 }}
                      className="flex items-center justify-between p-4 hover:bg-gray-50 transition-colors group"
                    >
                      <div className="flex items-center flex-1 min-w-0">
                        <div className="flex-shrink-0 mr-3">
                          {getFileIcon(file.content_type)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate">
                            {file.filename}
                          </p>
                          <div className="flex items-center text-xs text-gray-500 mt-1 gap-2">
                            <span>{formatFileSize(file.size)}</span>
                            <span>•</span>
                            <span>{file.content_type.split('/')[1].toUpperCase()}</span>
                            <span>•</span>
                            <span>{new Date(file.upload_timestamp).toLocaleTimeString()}</span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center space-x-3">
                        <CheckCircle className="h-5 w-5 text-success-500" />
                        <button
                          onClick={() => handleRemoveFile(file.id)}
                          disabled={deleteFileMutation.isLoading}
                          className="p-1 text-gray-400 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100"
                          title="Remove file"
                        >
                          {deleteFileMutation.isLoading ? (
                            <RefreshCw className="h-4 w-4 animate-spin" />
                          ) : (
                            <X className="h-4 w-4" />
                          )}
                        </button>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>
              <div className="card-footer">
                <div className="flex items-center justify-between">
                  <div className="text-sm text-gray-600">
                    Total: {uploadedFiles.length} files ({formatFileSize(
                      uploadedFiles.reduce((sum, file) => sum + file.size, 0)
                    )})
                  </div>
                  <div className="flex space-x-3">
                    {uploadedFiles.length > 0 ? (
                      <Link
                        to="/process"
                        className="btn btn-primary"
                      >
                        Proceed to Processing
                        <ArrowRight className="ml-1 h-4 w-4" />
                      </Link>
                    ) : (
                      <button
                        disabled
                        className="btn btn-primary opacity-50 cursor-not-allowed"
                      >
                        Proceed to Processing
                        <ArrowRight className="ml-1 h-4 w-4" />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Processing Tips */}
      {uploadedFiles.length === 0 && !isUploading && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="mt-8"
        >
          <div className="card bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200">
            <div className="card-body">
              <h3 className="text-lg font-semibold text-blue-900 mb-3">
                💡 Processing Tips
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm text-blue-800">
                <div>
                  <h4 className="font-medium mb-2">For Best Results:</h4>
                  <ul className="space-y-1">
                    <li>• Ensure documents are clearly scanned or photographed</li>
                    <li>• Use high-resolution images (300 DPI recommended)</li>
                    <li>• Keep documents flat and well-lit</li>
                    <li>• Rotate pages to correct orientation before uploading</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-medium mb-2">What Happens Next:</h4>
                  <ul className="space-y-1">
                    <li>• Azure AI extracts structured data from tax forms</li>
                    <li>• Gemini AI provides comprehensive analysis and categorization</li>
                    <li>• Professional workpapers are automatically generated</li>
                    <li>• All data can be exported in multiple formats</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {/* Next Steps (when files are uploaded) */}
      {hasUploadedFiles && !isUploading && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.5 }}
          className="mt-8"
        >
          <div className="card bg-gradient-to-r from-green-50 to-emerald-50 border-green-200">
            <div className="card-body">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-green-900 mb-2">
                    ✅ Files Ready for Processing
                  </h3>
                  <p className="text-green-700 mb-4">
                    You have {uploadedFiles.length} files ready to be processed. 
                    Click "Process Documents" to start AI analysis.
                  </p>
                  <div className="flex space-x-4">
                    <Link to="/process" className="btn btn-success">
                      Process Documents
                      <ArrowRight className="ml-1 h-4 w-4" />
                    </Link>
                    <button
                      onClick={() => {
                        const input = document.createElement('input')
                        input.type = 'file'
                        input.multiple = true
                        input.accept = '.pdf,.jpg,.jpeg,.png,.tiff,.tif'
                        input.onchange = (e) => {
                          const files = Array.from((e.target as HTMLInputElement).files || [])
                          onDrop(files, [])
                        }
                        input.click()
                      }}
                      className="btn btn-secondary"
                    >
                      <Plus className="h-4 w-4 mr-1" />
                      Add More Files
                    </button>
                  </div>
                </div>
                <div className="hidden lg:block text-6xl opacity-20">
                  📄
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  )
}

export default Upload
