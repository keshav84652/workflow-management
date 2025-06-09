import axios, { AxiosInstance, AxiosResponse } from 'axios'
import toast from 'react-hot-toast'
import { 
  FileUpload, 
  ProcessingBatch, 
  ProcessingConfig, 
  ProcessedDocument,
  WorkpaperMetadata,
  ApiResponse 
} from '../types'

// API base configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

class ApiService {
  private api: AxiosInstance

  constructor() {
    this.api = axios.create({
      baseURL: API_BASE_URL,
      timeout: 300000, // 5 minutes for long processing tasks
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Request interceptor
    this.api.interceptors.request.use(
      (config) => {
        // Add auth token if available
        const token = localStorage.getItem('auth_token')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )

    // Response interceptor
    this.api.interceptors.response.use(
      (response: AxiosResponse<ApiResponse<any>>) => {
        // Handle successful responses
        if (response.data?.error) {
          toast.error(response.data.error)
          throw new Error(response.data.error)
        }
        return response
      },
      (error) => {
        // Handle error responses
        const message = error.response?.data?.error || 
                       error.response?.data?.message || 
                       error.message || 
                       'An unexpected error occurred'
        
        toast.error(message)
        return Promise.reject(error)
      }
    )
  }

  // Health check
  async healthCheck(): Promise<boolean> {
    try {
      const response = await this.api.get('/health')
      return response.status === 200
    } catch (error) {
      return false
    }
  }

  // File upload endpoints
  async uploadFiles(files: File[]): Promise<FileUpload[]> {
    const formData = new FormData()
    files.forEach((file, index) => {
      formData.append(`file_${index}`, file)
    })

    const response = await this.api.post<ApiResponse<FileUpload[]>>('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total) {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          // Handle upload progress here if needed
          console.log(`Upload Progress: ${percentCompleted}%`)
        }
      },
    })

    return response.data.data || []
  }

  async deleteUploadedFile(fileId: string): Promise<void> {
    await this.api.delete(`/upload/${fileId}`)
  }

  async clearAllUploads(): Promise<void> {
    await this.api.delete('/upload/all')
  }

  // Document processing endpoints
  async processDocuments(
    fileIds: string[], 
    config: ProcessingConfig
  ): Promise<ProcessingBatch> {
    const response = await this.api.post<ApiResponse<ProcessingBatch>>('/process', {
      file_ids: fileIds,
      config: config
    })

    return response.data.data!
  }

  async getBatchStatus(batchId: string): Promise<ProcessingBatch> {
    const response = await this.api.get<ApiResponse<ProcessingBatch>>(`/process/batch/${batchId}`)
    return response.data.data!
  }

  async stopProcessing(batchId: string): Promise<void> {
    await this.api.post(`/process/batch/${batchId}/stop`)
  }

  // Results endpoints
  async getResults(batchId?: string): Promise<ProcessedDocument[]> {
    const url = batchId ? `/results?batch_id=${batchId}` : '/results'
    const response = await this.api.get<ApiResponse<ProcessedDocument[]>>(url)
    return response.data.data || []
  }

  async getDocumentDetails(documentId: string): Promise<ProcessedDocument> {
    const response = await this.api.get<ApiResponse<ProcessedDocument>>(`/results/document/${documentId}`)
    return response.data.data!
  }

  async exportResults(format: 'json' | 'csv', documentIds?: string[]): Promise<Blob> {
    const response = await this.api.post('/results/export', {
      format: format,
      document_ids: documentIds
    }, {
      responseType: 'blob'
    })

    return response.data
  }

  async compareResults(documentId: string): Promise<any> {
    const response = await this.api.get<ApiResponse<any>>(`/results/document/${documentId}/comparison`)
    return response.data.data!
  }

  // Workpaper generation endpoints
  async generateWorkpaper(
    batchId: string,
    config: {
      title: string
      client_name?: string
      preparer_name?: string
      tax_year?: string
    }
  ): Promise<WorkpaperMetadata> {
    const response = await this.api.post<ApiResponse<WorkpaperMetadata>>('/workpaper/generate', {
      batch_id: batchId,
      ...config
    })

    return response.data.data!
  }

  async downloadWorkpaper(workpaperId: string): Promise<Blob> {
    const response = await this.api.get(`/workpaper/${workpaperId}/download`, {
      responseType: 'blob'
    })

    return response.data
  }

  async getWorkpaperStatus(workpaperId: string): Promise<WorkpaperMetadata> {
    const response = await this.api.get<ApiResponse<WorkpaperMetadata>>(`/workpaper/${workpaperId}`)
    return response.data.data!
  }

  // Statistics and insights
  async getProcessingStats(): Promise<any> {
    const response = await this.api.get<ApiResponse<any>>('/stats')
    return response.data.data!
  }

  async getCategoryInsights(batchId?: string): Promise<any> {
    const url = batchId ? `/insights?batch_id=${batchId}` : '/insights'
    const response = await this.api.get<ApiResponse<any>>(url)
    return response.data.data!
  }

  // Configuration endpoints
  async getProcessingConfig(): Promise<ProcessingConfig> {
    const response = await this.api.get<ApiResponse<ProcessingConfig>>('/config')
    return response.data.data!
  }

  async updateProcessingConfig(config: ProcessingConfig): Promise<void> {
    await this.api.put('/config', config)
  }

  // Utility methods
  async validateDocument(file: File): Promise<boolean> {
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await this.api.post<ApiResponse<{ valid: boolean }>>('/validate', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })
      return response.data.data?.valid || false
    } catch (error) {
      return false
    }
  }

  async getSupportedFileTypes(): Promise<string[]> {
    const response = await this.api.get<ApiResponse<string[]>>('/supported-types')
    return response.data.data || []
  }

  // Error handling utility
  handleApiError(error: any): string {
    if (error.response?.data?.error) {
      return error.response.data.error
    }
    if (error.response?.data?.message) {
      return error.response.data.message
    }
    if (error.message) {
      return error.message
    }
    return 'An unexpected error occurred'
  }
}

// Create and export a singleton instance
export const apiService = new ApiService()
export default apiService

// Helper functions for common operations
export const withErrorHandling = async <T>(
  operation: () => Promise<T>,
  errorMessage?: string
): Promise<T | null> => {
  try {
    return await operation()
  } catch (error) {
    const message = errorMessage || apiService.handleApiError(error)
    toast.error(message)
    console.error('API operation failed:', error)
    return null
  }
}

export const withLoadingToast = async <T>(
  operation: () => Promise<T>,
  loadingMessage: string,
  successMessage?: string
): Promise<T | null> => {
  const toastId = toast.loading(loadingMessage)
  
  try {
    const result = await operation()
    toast.success(successMessage || 'Operation completed successfully', { id: toastId })
    return result
  } catch (error) {
    const errorMessage = apiService.handleApiError(error)
    toast.error(errorMessage, { id: toastId })
    console.error('API operation failed:', error)
    return null
  }
}
