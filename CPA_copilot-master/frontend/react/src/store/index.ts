import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { 
  FileUpload, 
  ProcessingBatch, 
  ProcessedDocument, 
  ProcessingConfig,
  WorkpaperMetadata
} from '../types'

interface AppState {
  // Upload state
  uploadedFiles: FileUpload[]
  setUploadedFiles: (files: FileUpload[]) => void
  addUploadedFiles: (files: FileUpload[]) => void
  removeUploadedFile: (fileId: string) => void
  clearUploadedFiles: () => void
  
  // Processing state
  processingConfig: ProcessingConfig
  setProcessingConfig: (config: ProcessingConfig) => void
  currentBatch: ProcessingBatch | null
  setCurrentBatch: (batch: ProcessingBatch | null) => void
  isProcessing: boolean
  setIsProcessing: (isProcessing: boolean) => void
  
  // Results state
  processedDocuments: ProcessedDocument[]
  setProcessedDocuments: (documents: ProcessedDocument[]) => void
  selectedDocumentIds: string[]
  toggleDocumentSelection: (documentId: string) => void
  clearDocumentSelection: () => void
  selectAllDocuments: () => void
  
  // Workpaper state
  workpaperMetadata: WorkpaperMetadata | null
  setWorkpaperMetadata: (metadata: WorkpaperMetadata | null) => void
  
  // UI state
  activePage: string
  setActivePage: (page: string) => void
  
  // Session management
  clearSession: () => void
  initializeSession: () => void
  
  // Computed values
  hasUploadedFiles: () => boolean
  hasProcessedDocuments: () => boolean
  getSelectedDocuments: () => ProcessedDocument[]
  getProcessingProgress: () => number
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // Upload state
      uploadedFiles: [],
      setUploadedFiles: (files) => set({ uploadedFiles: files }),
      addUploadedFiles: (files) => set((state) => ({ 
        uploadedFiles: [...state.uploadedFiles, ...files] 
      })),
      removeUploadedFile: (fileId) => set((state) => ({
        uploadedFiles: state.uploadedFiles.filter(f => f.id !== fileId)
      })),
      clearUploadedFiles: () => set({ uploadedFiles: [] }),
      
      // Processing state
      processingConfig: {
        enable_azure: true,
        enable_gemini: true,
        pii_mode: 'mask'
      },
      setProcessingConfig: (config) => set({ processingConfig: config }),
      currentBatch: null,
      setCurrentBatch: (batch) => set({ currentBatch: batch }),
      isProcessing: false,
      setIsProcessing: (isProcessing) => set({ isProcessing }),
      
      // Results state
      processedDocuments: [],
      setProcessedDocuments: (documents) => set({ processedDocuments: documents }),
      selectedDocumentIds: [],
      toggleDocumentSelection: (documentId) => set((state) => ({
        selectedDocumentIds: state.selectedDocumentIds.includes(documentId)
          ? state.selectedDocumentIds.filter(id => id !== documentId)
          : [...state.selectedDocumentIds, documentId]
      })),
      clearDocumentSelection: () => set({ selectedDocumentIds: [] }),
      selectAllDocuments: () => set((state) => ({
        selectedDocumentIds: state.processedDocuments.map(doc => doc.id)
      })),
      
      // Workpaper state
      workpaperMetadata: null,
      setWorkpaperMetadata: (metadata) => set({ workpaperMetadata: metadata }),
      
      // UI state
      activePage: '/',
      setActivePage: (page) => set({ activePage: page }),
      
      // Session management
      clearSession: () => set({
        uploadedFiles: [],
        currentBatch: null,
        processedDocuments: [],
        workpaperMetadata: null,
        isProcessing: false,
        selectedDocumentIds: [],
        activePage: '/'
      }),
      
      initializeSession: () => {
        // Clear any stale processing state on app initialization
        const state = get()
        if (state.isProcessing) {
          set({
            isProcessing: false,
          })
        }
      },
      
      // Computed values
      hasUploadedFiles: () => get().uploadedFiles.length > 0,
      hasProcessedDocuments: () => get().processedDocuments.length > 0,
      getSelectedDocuments: () => {
        const state = get()
        return state.processedDocuments.filter(doc => 
          state.selectedDocumentIds.includes(doc.id)
        )
      },
      getProcessingProgress: () => {
        const batch = get().currentBatch
        if (!batch || batch.total_documents === 0) return 0
        return (batch.processed_documents / batch.total_documents) * 100
      }
    }),
    {
      name: 'cpa-copilot-storage',
      partialize: (state) => ({
        uploadedFiles: state.uploadedFiles,
        processingConfig: state.processingConfig,
        processedDocuments: state.processedDocuments,
        workpaperMetadata: state.workpaperMetadata
      })
    }
  )
)

// Export typed hooks
export const useUploadedFiles = () => useAppStore(state => state.uploadedFiles)
export const useProcessingConfig = () => useAppStore(state => state.processingConfig)
export const useCurrentBatch = () => useAppStore(state => state.currentBatch)
export const useProcessedDocuments = () => useAppStore(state => state.processedDocuments)
export const useSelectedDocuments = () => useAppStore(state => state.getSelectedDocuments())
export const useHasUploadedFiles = () => useAppStore(state => state.hasUploadedFiles())
export const useHasProcessedDocuments = () => useAppStore(state => state.hasProcessedDocuments())
