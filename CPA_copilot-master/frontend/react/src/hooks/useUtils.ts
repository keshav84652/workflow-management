import { useState, useEffect, useCallback } from 'react'
import { useAppStore } from '../store'
import { ProcessingStatus } from '../types'

// Custom hook for file upload progress
export const useUploadProgress = () => {
  const [progress, setProgress] = useState(0)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadedCount, setUploadedCount] = useState(0)
  const [totalCount, setTotalCount] = useState(0)

  const startUpload = (total: number) => {
    setIsUploading(true)
    setProgress(0)
    setUploadedCount(0)
    setTotalCount(total)
  }

  const updateProgress = (completed: number) => {
    setUploadedCount(completed)
    setProgress((completed / totalCount) * 100)
  }

  const finishUpload = () => {
    setIsUploading(false)
    setProgress(100)
  }

  const resetUpload = () => {
    setIsUploading(false)
    setProgress(0)
    setUploadedCount(0)
    setTotalCount(0)
  }

  return {
    progress,
    isUploading,
    uploadedCount,
    totalCount,
    startUpload,
    updateProgress,
    finishUpload,
    resetUpload
  }
}

// Custom hook for processing progress
export const useProcessingProgress = () => {
  const currentBatch = useAppStore(state => state.currentBatch)
  const isProcessing = useAppStore(state => state.isProcessing)
  
  const progress = currentBatch ? 
    (currentBatch.processed_documents / currentBatch.total_documents) * 100 : 0
  
  const stats = {
    total: currentBatch?.total_documents || 0,
    completed: currentBatch?.processed_documents || 0,
    failed: currentBatch?.failed_documents || 0,
    inProgress: isProcessing,
    progress: Math.round(progress)
  }

  return stats
}

// Custom hook for application workflow state
export const useWorkflowState = () => {
  const hasUploadedFiles = useAppStore(state => state.hasUploadedFiles())
  const hasProcessedDocuments = useAppStore(state => state.hasProcessedDocuments())
  const currentBatch = useAppStore(state => state.currentBatch)
  const isProcessing = useAppStore(state => state.isProcessing)
  const workpaperMetadata = useAppStore(state => state.workpaperMetadata)

  // Determine current workflow step
  const getCurrentStep = useCallback(() => {
    if (workpaperMetadata) return 'workpaper_ready'
    if (hasProcessedDocuments) return 'results_ready'
    if (isProcessing) return 'processing'
    if (hasUploadedFiles) return 'ready_to_process'
    return 'upload_needed'
  }, [hasUploadedFiles, hasProcessedDocuments, isProcessing, workpaperMetadata])

  const currentStep = getCurrentStep()

  // Get next recommended action
  const getNextAction = useCallback(() => {
    switch (currentStep) {
      case 'upload_needed':
        return { action: 'upload', text: 'Upload Documents', path: '/upload' }
      case 'ready_to_process':
        return { action: 'process', text: 'Process Documents', path: '/process' }
      case 'processing':
        return { action: 'wait', text: 'Processing...', path: '/process' }
      case 'results_ready':
        return { action: 'workpaper', text: 'Generate Workpaper', path: '/workpaper' }
      case 'workpaper_ready':
        return { action: 'download', text: 'Download Workpaper', path: '/workpaper' }
      default:
        return { action: 'upload', text: 'Upload Documents', path: '/upload' }
    }
  }, [currentStep])

  const nextAction = getNextAction()

  // Get workflow progress percentage
  const getWorkflowProgress = useCallback(() => {
    switch (currentStep) {
      case 'upload_needed': return 0
      case 'ready_to_process': return 25
      case 'processing': return 50
      case 'results_ready': return 75
      case 'workpaper_ready': return 100
      default: return 0
    }
  }, [currentStep])

  const workflowProgress = getWorkflowProgress()

  return {
    currentStep,
    nextAction,
    workflowProgress,
    hasUploadedFiles,
    hasProcessedDocuments,
    isProcessing,
    currentBatch,
    workpaperMetadata
  }
}

// Custom hook for file validation
export const useFileValidation = () => {
  const validateFiles = useCallback((files: File[]) => {
    const maxSize = 10 * 1024 * 1024 // 10MB
    const allowedTypes = ['application/pdf', 'image/jpeg', 'image/png', 'image/tiff']
    const maxFiles = 20

    const errors: string[] = []
    const validFiles: File[] = []
    const invalidFiles: File[] = []

    if (files.length > maxFiles) {
      errors.push(`Maximum ${maxFiles} files allowed`)
      return { errors, validFiles: [], invalidFiles: files }
    }

    files.forEach(file => {
      if (file.size > maxSize) {
        errors.push(`${file.name} is too large (max 10MB)`)
        invalidFiles.push(file)
      } else if (!allowedTypes.includes(file.type)) {
        errors.push(`${file.name} is not a supported file type`)
        invalidFiles.push(file)
      } else {
        validFiles.push(file)
      }
    })

    return { errors, validFiles, invalidFiles }
  }, [])

  return { validateFiles }
}

// Custom hook for local storage persistence
export const useLocalStorage = <T>(key: string, initialValue: T) => {
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key)
      return item ? JSON.parse(item) : initialValue
    } catch (error) {
      console.error(`Error reading localStorage key "${key}":`, error)
      return initialValue
    }
  })

  const setValue = useCallback((value: T | ((val: T) => T)) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value
      setStoredValue(valueToStore)
      window.localStorage.setItem(key, JSON.stringify(valueToStore))
    } catch (error) {
      console.error(`Error setting localStorage key "${key}":`, error)
    }
  }, [key, storedValue])

  const removeValue = useCallback(() => {
    try {
      window.localStorage.removeItem(key)
      setStoredValue(initialValue)
    } catch (error) {
      console.error(`Error removing localStorage key "${key}":`, error)
    }
  }, [key, initialValue])

  return [storedValue, setValue, removeValue] as const
}

// Custom hook for document filtering and searching
export const useDocumentFilters = (documents: any[]) => {
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<ProcessingStatus | 'all'>('all')
  const [sortBy, setSortBy] = useState<'filename' | 'status' | 'processing_time'>('filename')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')

  const filteredDocuments = documents.filter(doc => {
    const matchesSearch = searchTerm === '' || 
      doc.filename?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      doc.category?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      doc.document_type?.toLowerCase().includes(searchTerm.toLowerCase())
    
    const matchesStatus = statusFilter === 'all' || doc.status === statusFilter
    
    return matchesSearch && matchesStatus
  })

  const sortedDocuments = [...filteredDocuments].sort((a, b) => {
    let aValue: any, bValue: any

    switch (sortBy) {
      case 'filename':
        aValue = a.filename || ''
        bValue = b.filename || ''
        break
      case 'status':
        aValue = a.status || ''
        bValue = b.status || ''
        break
      case 'processing_time':
        aValue = a.processing_time || 0
        bValue = b.processing_time || 0
        break
      default:
        aValue = a.filename || ''
        bValue = b.filename || ''
    }

    if (typeof aValue === 'string' && typeof bValue === 'string') {
      const comparison = aValue.localeCompare(bValue)
      return sortOrder === 'asc' ? comparison : -comparison
    } else {
      const comparison = aValue - bValue
      return sortOrder === 'asc' ? comparison : -comparison
    }
  })

  return {
    searchTerm,
    setSearchTerm,
    statusFilter,
    setStatusFilter,
    sortBy,
    setSortBy,
    sortOrder,
    setSortOrder,
    filteredDocuments: sortedDocuments,
    resultCount: sortedDocuments.length
  }
}

// Custom hook for toast notifications with consistent styling
export const useNotifications = () => {
  const showSuccess = useCallback((message: string) => {
    // This would use react-hot-toast which is already imported in the api service
    const { toast } = require('react-hot-toast')
    toast.success(message)
  }, [])

  const showError = useCallback((message: string) => {
    const { toast } = require('react-hot-toast')
    toast.error(message)
  }, [])

  const showInfo = useCallback((message: string) => {
    const { toast } = require('react-hot-toast')
    toast(message, { icon: 'ℹ️' })
  }, [])

  const showLoading = useCallback((message: string) => {
    const { toast } = require('react-hot-toast')
    return toast.loading(message)
  }, [])

  const dismiss = useCallback((toastId: string) => {
    const { toast } = require('react-hot-toast')
    toast.dismiss(toastId)
  }, [])

  return {
    showSuccess,
    showError,
    showInfo,
    showLoading,
    dismiss
  }
}
