import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  FileText,
  Download,
  Settings,
  User,
  Calendar,
  Building,
  BookOpen,
  CheckCircle,
  Clock,
  FileCheck,
  Eye,
  AlertCircle,
  BarChart3,
  Layers,
  Hash,
  RefreshCw,
  ArrowRight
} from 'lucide-react'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useGenerateWorkpaper, useDownloadWorkpaper } from '../hooks/useApi'
import { useAppStore } from '../store'
import { useWorkflowState } from '../hooks/useUtils'

interface WorkpaperConfig {
  title: string
  client_name: string
  preparer_name: string
  tax_year: string
}

interface WorkpaperMetadata {
  total_documents: number
  document_categories: Record<string, number>
  file_size_bytes: number
  page_count: number
  generation_date: string
}

const Workpaper: React.FC = () => {
  const [config, setConfig] = useState<WorkpaperConfig>({
    title: 'Tax Document Workpaper',
    client_name: '',
    preparer_name: '',
    tax_year: new Date().getFullYear().toString()
  })
  
  const [isDisplayingMockData, setIsDisplayingMockData] = useState(false);
  const currentBatch = useAppStore(state => state.currentBatch)
  const processedDocuments = useAppStore(state => state.processedDocuments)
  const workpaperMetadata = useAppStore(state => state.workpaperMetadata)
  const setWorkpaperMetadata = useAppStore(state => state.setWorkpaperMetadata)
  
  const { hasProcessedDocuments } = useWorkflowState()
  const generateMutation = useGenerateWorkpaper()
  const downloadMutation = useDownloadWorkpaper()

  // Create processing batch summary from real data
  const processingBatch = currentBatch ? {
    total_documents: currentBatch.total_documents,
    processed_documents: currentBatch.processed_documents,
    failed_documents: currentBatch.failed_documents,
    categories: processedDocuments.reduce((acc, doc) => {
      const category = doc.gemini_result?.document_category || 'Other Documents'
      acc[category] = (acc[category] || 0) + 1
      return acc
    }, {} as Record<string, number>),
    documents: processedDocuments.map(doc => ({
      filename: doc.file_upload.filename,
      gemini_result: doc.gemini_result
    }))
  } : {
    total_documents: 0,
    processed_documents: 0,
    failed_documents: 0,
    categories: {},
    documents: []
  }

  // Mock data fallback for demo purposes
  const mockProcessingBatch = {
    total_documents: 2,
    processed_documents: 2,
    failed_documents: 0,
    categories: {
      'Income Documents': 1,
      'Investment Documents': 1
    },
    documents: [
      {
        filename: 'TAX-1099-G.png',
        gemini_result: {
          suggested_bookmark_structure: {
            level1: 'Income Documents',
            level2: '1099-G',
            level3: '1099-G - STATE OF WASHINGTON'
          }
        }
      },
      {
        filename: 'TAX-1099-INT.png',
        gemini_result: {
          suggested_bookmark_structure: {
            level1: 'Investment Documents',
            level2: '1099-INT',
            level3: '1099-INT - CONTOSO BANK'
          }
        }
      }
    ]
  }

  useEffect(() => {
    if (!currentBatch && processedDocuments.length === 0) {
      setIsDisplayingMockData(true);
    } else {
      setIsDisplayingMockData(false);
    }
  }, [currentBatch, processedDocuments]);

  const displayBatch = !isDisplayingMockData && processingBatch?.total_documents > 0 ? processingBatch : mockProcessingBatch;

  const handleGenerateWorkpaper = async () => {
    if (!config.title.trim()) {
      toast.error('Please enter a workpaper title')
      return
    }

    if (!currentBatch?.id && displayBatch.total_documents === 0) {
      toast.error('No processed documents available for workpaper generation')
      return
    }

    try {
      const workpaperConfig = {
        title: config.title,
        client_name: config.client_name || undefined,
        preparer_name: config.preparer_name || undefined,
        tax_year: config.tax_year || undefined
      }

      // Use real API if we have a current batch, otherwise simulate for demo
      if (currentBatch?.id) {
        const metadata = await generateMutation.mutateAsync({
          batchId: currentBatch.id,
          config: workpaperConfig
        })
        setWorkpaperMetadata(metadata)
      } else {
        // Simulate for demo purposes
        await new Promise(resolve => setTimeout(resolve, 2000))
        const mockMetadata = {
          title: config.title,
          tax_year: config.tax_year,
          preparer_name: config.preparer_name,
          client_name: config.client_name,
          total_documents: displayBatch.total_documents,
          document_categories: displayBatch.categories,
          file_size_bytes: 2.4 * 1024 * 1024, // 2.4 MB
          page_count: 8,
          generation_date: new Date().toISOString()
        }
        setWorkpaperMetadata(mockMetadata)
      }
      
      toast.success('Workpaper generated successfully!')
    } catch (error) {
      console.error('Workpaper generation failed:', error)
      toast.error('Failed to generate workpaper')
    }
  }

  const handleDownloadWorkpaper = async () => {
    if (!workpaperMetadata) {
      toast.error('No workpaper available for download')
      return
    }

    try {
      if (currentBatch?.id) {
        // Use real API
        await downloadMutation.mutateAsync('workpaper-id') // This would be the actual workpaper ID
      } else {
        // Simulate download for demo
        toast.success('Workpaper download started (demo mode)')
      }
    } catch (error) {
      console.error('Download failed:', error)
      toast.error('Failed to download workpaper')
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
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
          Generate Workpaper
        </motion.h1>
        <motion.p 
          className="text-lg text-gray-600"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          Create professional PDF workpapers with intelligent bookmarks and organization
        </motion.p>
        <AnimatePresence>
        {isDisplayingMockData && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-center"
          >
            <AlertCircle className="h-5 w-5 text-amber-600 mr-2" />
            <p className="text-sm text-amber-700">
              No processed documents found. Displaying mock data for demonstration purposes.
            </p>
          </motion.div>
        )}
        </AnimatePresence>
      </div>

      {/* Document Summary */}

      {/* Document Summary */}
      <motion.div 
        className="card mb-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
      >
        <div className="card-header">
          <h3 className="text-lg font-semibold text-gray-900">Document Summary</h3>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center">
              <FileText className="h-8 w-8 text-primary-600 mx-auto mb-2" />
              <p className="text-2xl font-bold text-gray-900">{displayBatch.total_documents}</p>
              <p className="text-sm text-gray-600">Total Documents</p>
            </div>
            <div className="text-center">
              <CheckCircle className="h-8 w-8 text-success-600 mx-auto mb-2" />
              <p className="text-2xl font-bold text-gray-900">{displayBatch.processed_documents}</p>
              <p className="text-sm text-gray-600">Processed</p>
            </div>
            <div className="text-center">
              <Layers className="h-8 w-8 text-purple-600 mx-auto mb-2" />
              <p className="text-2xl font-bold text-gray-900">{Object.keys(displayBatch.categories).length}</p>
              <p className="text-sm text-gray-600">Categories</p>
            </div>
          </div>

          {/* Categories Breakdown */}
          <div className="mt-6">
            <h4 className="font-medium text-gray-900 mb-3">Document Categories</h4>
            <div className="space-y-2">
              {Object.entries(displayBatch.categories).map(([category, count]) => (
                <div key={category} className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center">
                    <BookOpen className="h-4 w-4 text-gray-500 mr-2" />
                    <span className="text-sm font-medium text-gray-900">{category}</span>
                  </div>
                  <span className="text-sm text-gray-600">{count} document{count !== 1 ? 's' : ''}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </motion.div>

      {/* Workpaper Configuration */}
      <motion.div 
        className="card mb-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.3 }}
      >
        <div className="card-header">
          <div className="flex items-center">
            <Settings className="h-5 w-5 text-gray-600 mr-2" />
            <h3 className="text-lg font-semibold text-gray-900">Workpaper Configuration</h3>
          </div>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="label">
                <FileText className="h-4 w-4 mr-1" />
                Workpaper Title
              </label>
              <input
                type="text"
                value={config.title}
                onChange={(e) => setConfig(prev => ({ ...prev, title: e.target.value }))}
                className="input"
                placeholder="Enter workpaper title"
              />
            </div>

            <div>
              <label className="label">
                <Calendar className="h-4 w-4 mr-1" />
                Tax Year
              </label>
              <input
                type="text"
                value={config.tax_year}
                onChange={(e) => setConfig(prev => ({ ...prev, tax_year: e.target.value }))}
                className="input"
                placeholder="e.g., 2023"
              />
            </div>

            <div>
              <label className="label">
                <User className="h-4 w-4 mr-1" />
                Client Name
              </label>
              <input
                type="text"
                value={config.client_name}
                onChange={(e) => setConfig(prev => ({ ...prev, client_name: e.target.value }))}
                className="input"
                placeholder="Enter client name (optional)"
              />
            </div>

            <div>
              <label className="label">
                <Building className="h-4 w-4 mr-1" />
                Preparer Name
              </label>
              <input
                type="text"
                value={config.preparer_name}
                onChange={(e) => setConfig(prev => ({ ...prev, preparer_name: e.target.value }))}
                className="input"
                placeholder="Enter preparer name (optional)"
              />
            </div>
          </div>
        </div>
      </motion.div>

      {/* Workpaper Preview Structure */}
      <motion.div 
        className="card mb-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.4 }}
      >
        <div className="card-header">
          <h3 className="text-lg font-semibold text-gray-900">Workpaper Structure Preview</h3>
        </div>
        <div className="card-body">
          <div className="space-y-3">
            <div className="flex items-center text-sm">
              <Hash className="h-4 w-4 text-gray-400 mr-2" />
              <span className="font-medium text-gray-900">Cover Page</span>
              <span className="ml-auto text-gray-500">Page 1</span>
            </div>
            <div className="flex items-center text-sm">
              <Hash className="h-4 w-4 text-gray-400 mr-2" />
              <span className="font-medium text-gray-900">Table of Contents</span>
              <span className="ml-auto text-gray-500">Page 2</span>
            </div>
            {Object.entries(displayBatch.categories).map(([category, count], index) => (
              <div key={category} className="ml-4 space-y-2">
                <div className="flex items-center text-sm">
                  <BookOpen className="h-4 w-4 text-primary-600 mr-2" />
                  <span className="font-medium text-gray-900">{category}</span>
                  <span className="ml-auto text-gray-500">Page {3 + index * 2}</span>
                </div>
                {displayBatch.documents
                  .filter(doc => doc.gemini_result?.suggested_bookmark_structure?.level1 === category)
                  .map((doc, docIndex) => (
                    <div key={doc.filename} className="ml-8 flex items-center text-sm">
                      <FileText className="h-4 w-4 text-gray-400 mr-2" />
                      <span className="text-gray-700">{doc.filename}</span>
                      <span className="ml-auto text-gray-500">Page {3 + index * 2 + docIndex + 1}</span>
                    </div>
                  ))}
              </div>
            ))}
          </div>
        </div>
      </motion.div>

      {/* Generation Controls */}
      <motion.div 
        className="card mb-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.5 }}
      >
        <div className="card-body">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-1">Generate Professional Workpaper</h3>
              <p className="text-sm text-gray-600">
                Create a consolidated PDF with intelligent bookmarks, cover page, and table of contents
              </p>
            </div>
            <div>
              {!generateMutation.isLoading && !workpaperMetadata ? (
                <button
                  onClick={handleGenerateWorkpaper}
                  disabled={displayBatch.total_documents === 0 || generateMutation.isLoading}
                  className="btn btn-primary btn-lg"
                >
                  <FileCheck className="h-5 w-5 mr-2" />
                  Generate Workpaper
                </button>
              ) : workpaperMetadata ? (
                <div className="flex space-x-3">
                  <button className="btn btn-secondary">
                    <Eye className="h-4 w-4 mr-1" />
                    Preview
                  </button>
                  <button
                    onClick={handleDownloadWorkpaper}
                    disabled={downloadMutation.isLoading}
                    className="btn btn-success btn-lg"
                  >
                    {downloadMutation.isLoading ? (
                      <RefreshCw className="h-5 w-5 mr-2 animate-spin" />
                    ) : (
                      <Download className="h-5 w-5 mr-2" />
                    )}
                    Download PDF
                  </button>
                </div>
              ) : (
                <button disabled className="btn btn-primary btn-lg opacity-50">
                  <RefreshCw className="h-5 w-5 mr-2 animate-spin" />
                  Generating...
                </button>
              )}
            </div>
          </div>
        </div>
      </motion.div>

      {/* Generation Progress */}
      <AnimatePresence>
        {generateMutation.isLoading && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
            className="card mb-6"
          >
            <div className="card-header">
              <h3 className="text-lg font-semibold text-gray-900">Generating Workpaper</h3>
            </div>
            <div className="card-body">
              <div className="flex items-center justify-center py-8">
                <div className="text-center">
                  <RefreshCw className="h-8 w-8 text-primary-600 mx-auto mb-4 animate-spin" />
                  <p className="text-lg font-medium text-gray-900 mb-2">Creating Professional Workpaper</p>
                  <p className="text-sm text-gray-600">
                    Processing documents and generating PDF with bookmarks...
                  </p>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Generated Workpaper Information */}
      <AnimatePresence>
        {workpaperMetadata && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
            className="card"
          >
            <div className="card-header">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">Workpaper Generated Successfully</h3>
                <CheckCircle className="h-6 w-6 text-success-500" />
              </div>
            </div>
            <div className="card-body">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                <div className="text-center">
                  <Hash className="h-8 w-8 text-primary-600 mx-auto mb-2" />
                  <p className="text-2xl font-bold text-gray-900">{workpaperMetadata.page_count}</p>
                  <p className="text-sm text-gray-600">Total Pages</p>
                </div>
                <div className="text-center">
                  <FileText className="h-8 w-8 text-success-600 mx-auto mb-2" />
                  <p className="text-2xl font-bold text-gray-900">{formatFileSize(workpaperMetadata.file_size_bytes || 0)}</p>
                  <p className="text-sm text-gray-600">File Size</p>
                </div>
                <div className="text-center">
                  <Layers className="h-8 w-8 text-purple-600 mx-auto mb-2" />
                  <p className="text-2xl font-bold text-gray-900">{workpaperMetadata.total_documents}</p>
                  <p className="text-sm text-gray-600">Documents</p>
                </div>
              </div>

              <div className="bg-success-50 border border-success-200 rounded-lg p-4">
                <div className="flex items-start">
                  <CheckCircle className="h-5 w-5 text-success-600 mt-0.5 mr-3" />
                  <div>
                    <h4 className="font-medium text-success-900 mb-1">Workpaper Features</h4>
                    <ul className="text-sm text-success-800 space-y-1">
                      <li>• Professional cover page with client and preparer information</li>
                      <li>• Comprehensive table of contents with accurate page numbers</li>
                      <li>• Hierarchical bookmarks for easy navigation (3 levels)</li>
                      <li>• Organized by document category and type</li>
                      <li>• High-quality document images preserved</li>
                    </ul>
                  </div>
                </div>
              </div>

              <div className="flex justify-center mt-6">
                <button
                  onClick={handleDownloadWorkpaper}
                  disabled={downloadMutation.isLoading}
                  className="btn btn-primary btn-lg"
                >
                  {downloadMutation.isLoading ? (
                    <RefreshCw className="h-5 w-5 mr-2 animate-spin" />
                  ) : (
                    <Download className="h-5 w-5 mr-2" />
                  )}
                  Download Professional Workpaper
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* No Documents Message */}
      {displayBatch.total_documents === 0 && !hasProcessedDocuments && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.6 }}
        >
          <div className="card text-center py-12">
            <div className="card-body">
              <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No Processed Documents</h3>
              <p className="text-gray-600 mb-6">
                Process documents first to generate professional workpapers
              </p>
              <Link to="/process" className="btn btn-primary">
                <ArrowRight className="h-4 w-4 mr-1" />
                Go to Processing
              </Link>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  )
}

export default Workpaper
