import { useQuery, useMutation, useQueryClient } from 'react-query'
import { apiService, withErrorHandling, withLoadingToast } from '../services/api'
import { useAppStore } from '../store'
import { 
  FileUpload, 
  ProcessingBatch, 
  ProcessingConfig, 
  ProcessedDocument,
  WorkpaperMetadata 
} from '../types'

// Upload hooks
export const useUploadFiles = () => {
  const queryClient = useQueryClient()
  const addUploadedFiles = useAppStore(state => state.addUploadedFiles)
  
  return useMutation({
    mutationFn: (files: File[]) => apiService.uploadFiles(files),
    onSuccess: (uploadedFiles: FileUpload[]) => {
      addUploadedFiles(uploadedFiles)
      queryClient.invalidateQueries(['uploadedFiles'])
    },
    onError: (error) => {
      console.error('Upload failed:', error)
    }
  })
}

export const useDeleteFile = () => {
  const queryClient = useQueryClient()
  const removeUploadedFile = useAppStore(state => state.removeUploadedFile)
  
  return useMutation({
    mutationFn: (fileId: string) => apiService.deleteUploadedFile(fileId),
    onSuccess: (_, fileId) => {
      removeUploadedFile(fileId)
      queryClient.invalidateQueries(['uploadedFiles'])
    }
  })
}

export const useClearAllFiles = () => {
  const queryClient = useQueryClient()
  const clearUploadedFiles = useAppStore(state => state.clearUploadedFiles)
  
  return useMutation({
    mutationFn: () => apiService.clearAllUploads(), // This attempts to clear backend
    onSettled: () => {
      // Always clear frontend state regardless of backend success/failure
      // This addresses the issue where demo files might persist in UI if backend is down
      clearUploadedFiles()
      queryClient.invalidateQueries(['uploadedFiles']) // Refetch to confirm (will be empty if backend is down)
    },
    onError: (error) => {
      // Error toast is already handled by apiService interceptor
      // Log for debugging, but frontend state is cleared in onSettled
      console.error('Clear all files backend call failed:', error)
    }
  })
}

// Processing hooks
export const useProcessDocuments = () => {
  const queryClient = useQueryClient()
  const { setCurrentBatch, setIsProcessing } = useAppStore()
  
  return useMutation({
    mutationFn: ({ fileIds, config }: { fileIds: string[], config: ProcessingConfig }) => 
      apiService.processDocuments(fileIds, config),
    onSuccess: (batch: ProcessingBatch) => {
      setCurrentBatch(batch)
      setIsProcessing(true)
      queryClient.invalidateQueries(['processingBatch', batch.id])
    },
    onError: () => {
      setIsProcessing(false)
    }
  })
}

export const useBatchStatus = (batchId?: string, enabled = false) => {
  const { setCurrentBatch, setIsProcessing, setProcessedDocuments } = useAppStore()
  
  return useQuery({
    queryKey: ['processingBatch', batchId],
    queryFn: () => apiService.getBatchStatus(batchId!),
    enabled: enabled && !!batchId,
    refetchInterval: (data) => {
      // Stop polling if processing is complete
      if (data?.status === 'completed' || data?.status === 'error') {
        return false
      }
      return 2000 // Poll every 2 seconds
    },
    onSuccess: (batch: ProcessingBatch) => {
      setCurrentBatch(batch)
      if (batch.status === 'completed' || batch.status === 'error') {
        setIsProcessing(false)
        setProcessedDocuments(batch.documents)
      }
    }
  })
}

export const useStopProcessing = () => {
  const queryClient = useQueryClient()
  const setIsProcessing = useAppStore(state => state.setIsProcessing)
  
  return useMutation({
    mutationFn: (batchId: string) => apiService.stopProcessing(batchId),
    onSuccess: () => {
      setIsProcessing(false)
      queryClient.invalidateQueries(['processingBatch'])
    }
  })
}

// Results hooks
export const useResults = (batchId?: string) => {
  return useQuery({
    queryKey: ['results', batchId],
    queryFn: () => apiService.getResults(batchId),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

export const useDocumentDetails = (documentId: string, enabled = false) => {
  return useQuery({
    queryKey: ['documentDetails', documentId],
    queryFn: () => apiService.getDocumentDetails(documentId),
    enabled: enabled && !!documentId,
  })
}

export const useExportResults = () => {
  return useMutation({
    mutationFn: ({ format, documentIds }: { format: 'json' | 'csv', documentIds?: string[] }) =>
      apiService.exportResults(format, documentIds),
    onSuccess: (blob, variables) => {
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `cpa-copilot-results.${variables.format}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    }
  })
}

// Workpaper hooks
export const useGenerateWorkpaper = () => {
  const queryClient = useQueryClient()
  const setWorkpaperMetadata = useAppStore(state => state.setWorkpaperMetadata)
  
  return useMutation({
    mutationFn: ({ batchId, config }: { 
      batchId: string, 
      config: { title: string, client_name?: string, preparer_name?: string, tax_year?: string } 
    }) => apiService.generateWorkpaper(batchId, config),
    onSuccess: (metadata: WorkpaperMetadata) => {
      setWorkpaperMetadata(metadata)
      queryClient.invalidateQueries(['workpaper'])
    }
  })
}

export const useDownloadWorkpaper = () => {
  return useMutation({
    mutationFn: (workpaperId: string) => apiService.downloadWorkpaper(workpaperId),
    onSuccess: (blob) => {
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'workpaper.pdf'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    }
  })
}

// Configuration hooks
export const useProcessingConfig = () => {
  return useQuery({
    queryKey: ['processingConfig'],
    queryFn: () => apiService.getProcessingConfig(),
    staleTime: 10 * 60 * 1000, // 10 minutes
  })
}

export const useUpdateProcessingConfig = () => {
  const queryClient = useQueryClient()
  const setProcessingConfig = useAppStore(state => state.setProcessingConfig)
  
  return useMutation({
    mutationFn: (config: ProcessingConfig) => apiService.updateProcessingConfig(config),
    onSuccess: (_, config) => {
      setProcessingConfig(config)
      queryClient.invalidateQueries(['processingConfig'])
    }
  })
}

// Stats hooks
export const useProcessingStats = () => {
  return useQuery({
    queryKey: ['processingStats'],
    queryFn: () => apiService.getProcessingStats(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

export const useCategoryInsights = (batchId?: string) => {
  return useQuery({
    queryKey: ['categoryInsights', batchId],
    queryFn: () => apiService.getCategoryInsights(batchId),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

// Document visualization hook (for future implementation)
export const useDocumentVisualization = () => {
  return useMutation(
    async ({ documentId, visualizationType }: { documentId: string, visualizationType: 'box' | 'tick' }) => {
      // This will need to be implemented as an endpoint in the backend
      const response = await fetch(`/api/documents/${documentId}/visualization?type=${visualizationType}`)
      return response.blob()
    },
    {
      onSuccess: (blob) => {
        const url = window.URL.createObjectURL(blob)
        return url
      }
    }
  )
}

// Health check hook
export const useHealthCheck = () => {
  return useQuery({
    queryKey: ['healthCheck'],
    queryFn: () => apiService.healthCheck(),
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 60 * 1000, // 1 minute
  })
}
