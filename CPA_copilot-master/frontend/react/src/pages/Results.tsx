import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  BarChart3,
  FileText,
  Download,
  Eye,
  CheckCircle,
  AlertCircle,
  Clock,
  TrendingUp,
  Building2,
  Sparkles,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Filter,
  Search,
  Calendar,
  DollarSign,
  Image,
  RefreshCw
} from 'lucide-react'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import { ProcessedDocument, ProcessingStatus, DocumentSummary } from '../types'
import { useResults, useExportResults } from '../hooks/useApi'
import { useDocumentFilters } from '../hooks/useUtils'
import { useAppStore } from '../store'
import DocumentVisualization from '../components/DocumentVisualization'
import { exportToCSV, exportKeyFieldsToCSV, exportSummaryToCSV } from '../utils/csvExport'

const Results: React.FC = () => {
  const [expandedDocuments, setExpandedDocuments] = useState<Set<string>>(new Set())
  const [selectedDocuments, setSelectedDocuments] = useState<Set<string>>(new Set())
  const [visualizationType, setVisualizationType] = useState<'box' | 'tick'>('box')
  const [visualizationModal, setVisualizationModal] = useState<{
    isOpen: boolean
    documentId: string
    filename: string
  }>({ isOpen: false, documentId: '', filename: '' })
  
  const currentBatch = useAppStore(state => state.currentBatch)
  const processedDocuments = useAppStore(state => state.processedDocuments)
  
  // Fetch results data
  const { data: resultsData, isLoading, error, refetch } = useResults(currentBatch?.id)
  const [isDisplayingMockData, setIsDisplayingMockData] = useState(false)
  const exportMutation = useExportResults()

  useEffect(() => {
    if (!isLoading && (error || (documentSummaries.length === 0 && !currentBatch?.id && !processedDocuments.length))) {
      setIsDisplayingMockData(true)
    } else {
      setIsDisplayingMockData(false)
    }
  }, [isLoading, error, documentSummaries, currentBatch, processedDocuments])

  // Convert ProcessedDocument[] to DocumentSummary[] for display
  const documentSummaries: DocumentSummary[] = (resultsData || processedDocuments).map(doc => ({
    filename: doc.file_upload.filename,
    status: doc.processing_status,
    processing_time: doc.processing_end_time && doc.processing_start_time ?
      (new Date(doc.processing_end_time).getTime() - new Date(doc.processing_start_time).getTime()) / 1000 : undefined,
    document_type: doc.azure_result?.doc_type,
    confidence: doc.azure_result?.confidence,
    category: doc.gemini_result?.document_category,
    key_fields: {
      ...doc.azure_result?.fields,
      ...doc.gemini_result?.extracted_key_info
    },
    validation_issues: doc.validation_errors.length,
    analysis_summary: doc.gemini_result?.document_analysis_summary,
    bookmark_path: doc.gemini_result?.suggested_bookmark_structure ?
      `${doc.gemini_result.suggested_bookmark_structure.level1} > ${doc.gemini_result.suggested_bookmark_structure.level2} > ${doc.gemini_result.suggested_bookmark_structure.level3}` : undefined
  }))

  // Use document filters hook
  const {
    searchTerm,
    setSearchTerm,
    statusFilter,
    setStatusFilter,
    sortBy,
    setSortBy,
    sortOrder,
    setSortOrder,
    filteredDocuments,
    resultCount
  } = useDocumentFilters(documentSummaries)

  // Mock processed documents for fallback - in real app, this would come from API/state management
  const mockProcessedDocuments: DocumentSummary[] = [
    {
      filename: 'TAX-1099-G.png',
      status: ProcessingStatus.COMPLETED,
      processing_time: 25.1,
      document_type: 'tax.us.1099G.2022',
      confidence: 0.782,
      category: 'Income Documents',
      key_fields: {
        'TaxYear': '2023',
        'Payer_Name': 'STATE OF WASHINGTON - Department of Labour',
        'Box1': 123456,
        'Box2': 12.35
      },
      validation_issues: 0,
      analysis_summary: 'This Form 1099-G reports unemployment compensation and state tax refunds for 2023.',
      bookmark_path: 'Income Documents > 1099-G > STATE OF WASHINGTON'
    },
    {
      filename: 'TAX-1099-INT.png',
      status: ProcessingStatus.COMPLETED,
      processing_time: 44.8,
      document_type: 'tax.us.1099INT.2022',
      confidence: 0.335,
      category: 'Investment Documents',
      key_fields: {
        'TaxYear': '2023',
        'Payer_Name': 'CONTOSO BANK',
        'Box1': 123456,
        'Box4': 987
      },
      validation_issues: 0,
      analysis_summary: 'Form 1099-INT reporting significant interest income with federal tax withheld.',
      bookmark_path: 'Investment Documents > 1099-INT > CONTOSO BANK'
    }
  ]

  // Use real data if available, otherwise fall back to mock data
  const displayDocuments = isDisplayingMockData ? mockProcessedDocuments : filteredDocuments;
  
  const stats = {
    total: displayDocuments.length,
    successful: displayDocuments.filter(d => d.status === ProcessingStatus.COMPLETED).length,
    failed: displayDocuments.filter(d => d.status === ProcessingStatus.ERROR).length,
    warnings: displayDocuments.reduce((sum, d) => sum + d.validation_issues, 0),
    avgProcessingTime: displayDocuments.reduce((sum, d) => sum + (d.processing_time || 0), 0) / displayDocuments.length || 0
  }

  const toggleDocumentExpansion = (filename: string) => {
    const newExpanded = new Set(expandedDocuments)
    if (newExpanded.has(filename)) {
      newExpanded.delete(filename)
    } else {
      newExpanded.add(filename)
    }
    setExpandedDocuments(newExpanded)
  }

  const toggleDocumentSelection = (filename: string) => {
    const newSelected = new Set(selectedDocuments)
    if (newSelected.has(filename)) {
      newSelected.delete(filename)
    } else {
      newSelected.add(filename)
    }
    setSelectedDocuments(newSelected)
  }

  const selectAllDocuments = () => {
    if (selectedDocuments.size === displayDocuments.length) {
      setSelectedDocuments(new Set())
    } else {
      setSelectedDocuments(new Set(displayDocuments.map(doc => doc.filename)))
    }
  }

  const handleExport = async (format: 'json' | 'csv', exportType: 'standard' | 'key-fields' | 'summary' = 'standard') => {
    const selectedIds = Array.from(selectedDocuments)
    const documentsToExport = selectedDocuments.size > 0
      ? displayDocuments.filter(doc => selectedDocuments.has(doc.filename))
      : displayDocuments
    
    if (format === 'csv') {
      // Use local CSV export
      try {
        switch (exportType) {
          case 'key-fields':
            exportKeyFieldsToCSV(documentsToExport)
            toast.success('Key fields exported to CSV')
            break
          case 'summary':
            exportSummaryToCSV(documentsToExport)
            toast.success('Summary exported to CSV')
            break
          default:
            exportToCSV(documentsToExport)
            toast.success('Results exported to CSV')
        }
      } catch (error) {
        console.error('CSV export failed:', error)
        toast.error('Failed to export CSV')
      }
    } else {
      // Use API for JSON export
      try {
        await exportMutation.mutateAsync({ format, documentIds: selectedIds.length > 0 ? selectedIds : undefined })
      } catch (error) {
        console.error('Export failed:', error)
      }
    }
  }

  const handleViewVisualization = (filename: string) => {
    const actualDoc = (resultsData || processedDocuments).find(doc => doc.file_upload?.filename === filename);
    const actualDocumentId = actualDoc ? actualDoc.id : filename;
    setVisualizationModal({
      isOpen: true,
      documentId: actualDocumentId,
      filename
    })
  }

  const closeVisualizationModal = () => {
    setVisualizationModal({
      isOpen: false,
      documentId: '',
      filename: ''
    })
  }

  const getStatusIcon = (status: ProcessingStatus) => {
    switch (status) {
      case ProcessingStatus.COMPLETED:
        return <CheckCircle className="h-5 w-5 text-success-500" />
      case ProcessingStatus.ERROR:
        return <AlertCircle className="h-5 w-5 text-error-500" />
      case ProcessingStatus.PROCESSING:
        return <Clock className="h-5 w-5 text-warning-500 animate-pulse" />
      default:
        return <Clock className="h-5 w-5 text-gray-400" />
    }
  }

  const getStatusBadge = (status: ProcessingStatus) => {
    switch (status) {
      case ProcessingStatus.COMPLETED:
        return <span className="badge badge-success">Completed</span>
      case ProcessingStatus.ERROR:
        return <span className="badge badge-error">Failed</span>
      case ProcessingStatus.PROCESSING:
        return <span className="badge badge-warning">Processing</span>
      default:
        return <span className="badge badge-info">Pending</span>
    }
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <motion.h1 
          className="text-3xl font-bold text-gray-900 mb-2"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          Processing Results
        </motion.h1>
        <motion.p 
          className="text-lg text-gray-600"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          Review extracted data and AI analysis results
        </motion.p>
        <AnimatePresence>
        {isDisplayingMockData && !isLoading && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-center"
          >
            <AlertCircle className="h-5 w-5 text-amber-600 mr-2" />
            <p className="text-sm text-amber-700">
              {error ? 'Error loading results. ' : 'No data available. '}Displaying mock data for demonstration purposes.
            </p>
          </motion.div>
        )}
        </AnimatePresence>
      </div>

      {/* Summary Statistics */}
      <motion.div 
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
      >
        <div className="card">
          <div className="card-body text-center">
            <FileText className="h-8 w-8 text-primary-600 mx-auto mb-2" />
            <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
            <p className="text-sm text-gray-600">Total Documents</p>
          </div>
        </div>

        <div className="card">
          <div className="card-body text-center">
            <CheckCircle className="h-8 w-8 text-success-600 mx-auto mb-2" />
            <p className="text-2xl font-bold text-gray-900">{stats.successful}</p>
            <p className="text-sm text-gray-600">Successful</p>
          </div>
        </div>

        <div className="card">
          <div className="card-body text-center">
            <AlertCircle className="h-8 w-8 text-error-600 mx-auto mb-2" />
            <p className="text-2xl font-bold text-gray-900">{stats.failed}</p>
            <p className="text-sm text-gray-600">Failed</p>
          </div>
        </div>

        <div className="card">
          <div className="card-body text-center">
            <Clock className="h-8 w-8 text-warning-600 mx-auto mb-2" />
            <p className="text-2xl font-bold text-gray-900">{stats.avgProcessingTime.toFixed(1)}s</p>
            <p className="text-sm text-gray-600">Avg Time</p>
          </div>
        </div>

        <div className="card">
          <div className="card-body text-center">
            <TrendingUp className="h-8 w-8 text-purple-600 mx-auto mb-2" />
            <p className="text-2xl font-bold text-gray-900">{stats.warnings}</p>
            <p className="text-sm text-gray-600">Warnings</p>
          </div>
        </div>
      </motion.div>

      {/* Controls and Filters */}
      <motion.div 
        className="card mb-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.3 }}
      >
        <div className="card-body">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">
            <div className="flex flex-col md:flex-row md:items-center space-y-4 md:space-y-0 md:space-x-4">
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search documents..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="input pl-10 w-64"
                />
              </div>

              {/* Status Filter */}
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as any)}
                className="input w-40"
                title="Filter by processing status"
                aria-label="Filter by processing status"
              >
                <option value="all">All Statuses</option>
                <option value={ProcessingStatus.COMPLETED}>Completed</option>
                <option value={ProcessingStatus.ERROR}>Failed</option>
                <option value={ProcessingStatus.PROCESSING}>Processing</option>
              </select>

              {/* Sort By */}
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="input w-40"
                title="Sort documents by"
                aria-label="Sort documents by"
              >
                <option value="filename">Sort by Name</option>
                <option value="status">Sort by Status</option>
                <option value="processing_time">Sort by Time</option>
              </select>

              {/* Visualization Type */}
              <select
                value={visualizationType}
                onChange={(e) => setVisualizationType(e.target.value as any)}
                className="input w-40"
                title="Visualization annotation type"
                aria-label="Visualization annotation type"
              >
                <option value="box">Box Annotations</option>
                <option value="tick">Tick Marks</option>
              </select>
            </div>

            {/* Export and Selection Controls */}
            <div className="flex items-center space-x-3">
              <button
                onClick={selectAllDocuments}
                className="btn btn-secondary btn-sm"
              >
                {selectedDocuments.size === displayDocuments.length ? 'Deselect All' : 'Select All'}
              </button>
              <span className="text-sm text-gray-600">
                {selectedDocuments.size} selected
              </span>
              
              {/* Export Dropdown */}
              <div className="relative group">
                <button className="btn btn-secondary btn-sm">
                  <Download className="h-4 w-4 mr-1" />
                  Export
                  <ChevronDown className="h-3 w-3 ml-1" />
                </button>
                <div className="absolute right-0 mt-1 w-48 bg-white border border-gray-200 rounded-md shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-10">
                  <div className="py-1">
                    <button
                      onClick={() => handleExport('json')}
                      disabled={exportMutation.isLoading}
                      className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 disabled:opacity-50"
                    >
                      Export as JSON
                    </button>
                    <button
                      onClick={() => handleExport('csv', 'standard')}
                      className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      Export as CSV (Standard)
                    </button>
                    <button
                      onClick={() => handleExport('csv', 'key-fields')}
                      className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      Export as CSV (Key Fields)
                    </button>
                    <button
                      onClick={() => handleExport('csv', 'summary')}
                      className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      Export as CSV (Summary)
                    </button>
                  </div>
                </div>
              </div>
              
              <button
                onClick={() => refetch()}
                disabled={isLoading}
                className="btn btn-secondary btn-sm"
              >
                {isLoading ? (
                  <RefreshCw className="h-4 w-4 mr-1 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4 mr-1" />
                )}
                Refresh
              </button>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Document Results */}
      <motion.div 
        className="card"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.4 }}
      >
        <div className="card-header">
          <h3 className="text-lg font-semibold text-gray-900">
            Document Analysis Results ({resultCount})
          </h3>
          {isLoading && (
            <div className="flex items-center text-sm text-gray-600">
              <RefreshCw className="h-4 w-4 mr-1 animate-spin" />
              Loading results...
            </div>
          )}
        </div>
        <div className="card-body p-0">
          {displayDocuments.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No Results Found</h3>
              <p className="text-gray-600">Try adjusting your search or filter criteria</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {displayDocuments.map((doc, index) => (
                <motion.div
                  key={doc.filename}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, delay: index * 0.1 }}
                  className="p-6 hover:bg-gray-50 transition-colors"
                >
                  {/* Document Header */}
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center space-x-4">
                      <input
                        type="checkbox"
                        checked={selectedDocuments.has(doc.filename)}
                        onChange={() => toggleDocumentSelection(doc.filename)}
                        className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                        title={`Select ${doc.filename}`}
                        aria-label={`Select ${doc.filename}`}
                      />
                      <button
                        onClick={() => toggleDocumentExpansion(doc.filename)}
                        className="p-1 rounded hover:bg-gray-200 transition-colors"
                      >
                        {expandedDocuments.has(doc.filename) ? (
                          <ChevronDown className="h-5 w-5 text-gray-500" />
                        ) : (
                          <ChevronRight className="h-5 w-5 text-gray-500" />
                        )}
                      </button>
                      <div>
                        <h4 className="text-lg font-medium text-gray-900">{doc.filename}</h4>
                        <div className="flex items-center space-x-4 text-sm text-gray-600">
                          <span>{doc.document_type || 'Unknown Type'}</span>
                          <span>•</span>
                          <span>{doc.processing_time?.toFixed(1) || '0'}s</span>
                          {doc.confidence && (
                            <>
                              <span>•</span>
                              <span>{(doc.confidence * 100).toFixed(0)}% confidence</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-3">
                      {getStatusIcon(doc.status)}
                      {getStatusBadge(doc.status)}
                    </div>
                  </div>

                  {/* Quick Overview */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-4">
                    <div>
                      <h5 className="font-medium text-gray-900 mb-2">Azure Analysis</h5>
                      <div className="space-y-1 text-sm">
                        <div className="flex items-center">
                          <Building2 className="h-4 w-4 text-blue-600 mr-2" />
                          <span>Document Type: {doc.document_type}</span>
                        </div>
                        <div className="flex items-center">
                          <TrendingUp className="h-4 w-4 text-blue-600 mr-2" />
                          <span>Confidence: {doc.confidence ? `${(doc.confidence * 100).toFixed(0)}%` : 'N/A'}</span>
                        </div>
                      </div>
                    </div>
                    <div>
                      <h5 className="font-medium text-gray-900 mb-2">Gemini Analysis</h5>
                      <div className="space-y-1 text-sm">
                        <div className="flex items-center">
                          <Sparkles className="h-4 w-4 text-purple-600 mr-2" />
                          <span>Category: {doc.category}</span>
                        </div>
                        <div className="flex items-center">
                          <FileText className="h-4 w-4 text-purple-600 mr-2" />
                          <span>Path: {doc.bookmark_path}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Expanded Details */}
                  <AnimatePresence>
                    {expandedDocuments.has(doc.filename) && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.3 }}
                        className="border-t border-gray-200 pt-4 mt-4"
                      >
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                          {/* Key Fields */}
                          <div>
                            <h5 className="font-medium text-gray-900 mb-3">Extracted Key Fields</h5>
                            <div className="space-y-2">
                              {Object.entries(doc.key_fields).map(([field, value]) => (
                                <div key={field} className="flex justify-between items-center py-1">
                                  <span className="text-sm text-gray-600">{field}:</span>
                                  <span className="text-sm font-medium text-gray-900">
                                    {typeof value === 'number' ? value.toLocaleString() : String(value || '')}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>

                          {/* Analysis Summary */}
                          <div>
                            <h5 className="font-medium text-gray-900 mb-3">AI Analysis Summary</h5>
                            <p className="text-sm text-gray-600 leading-relaxed">
                              {doc.analysis_summary}
                            </p>
                            
                            {doc.validation_issues > 0 && (
                              <div className="mt-3 p-3 bg-warning-50 border border-warning-200 rounded-lg">
                                <div className="flex items-center">
                                  <AlertCircle className="h-4 w-4 text-warning-600 mr-2" />
                                  <span className="text-sm font-medium text-warning-800">
                                    {doc.validation_issues} validation issue(s) found
                                  </span>
                                </div>
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Action Buttons */}
                        <div className="flex justify-end space-x-3 mt-4 pt-4 border-t border-gray-200">
                          <button
                            onClick={() => handleViewVisualization(doc.filename, doc.filename)}
                            className="btn btn-secondary btn-sm"
                          >
                            <Image className="h-4 w-4 mr-1" />
                            View Visualization
                          </button>
                          <button className="btn btn-secondary btn-sm">
                            <Eye className="h-4 w-4 mr-1" />
                            View Details
                          </button>
                          <button
                            onClick={() => handleExport('json')}
                            className="btn btn-secondary btn-sm"
                          >
                            <Download className="h-4 w-4 mr-1" />
                            Export
                          </button>
                          <button className="btn btn-secondary btn-sm">
                            <ExternalLink className="h-4 w-4 mr-1" />
                            Raw Data
                          </button>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </motion.div>

      {/* No Results Message */}
      {displayDocuments.length === 0 && !isLoading && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.5 }}
        >
          <div className="card text-center py-12">
            <div className="card-body">
              <BarChart3 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No Processing Results</h3>
              <p className="text-gray-600 mb-6">
                {processedDocuments.length === 0
                  ? 'Process documents first to see AI analysis results here'
                  : 'No documents match your current filters'
                }
              </p>
              {processedDocuments.length === 0 ? (
                <Link to="/process" className="btn btn-primary">
                  Go to Processing
                </Link>
              ) : (
                <button
                  onClick={() => {
                    setSearchTerm('')
                    setStatusFilter('all')
                  }}
                  className="btn btn-secondary"
                >
                  Clear Filters
                </button>
              )}
            </div>
          </div>
        </motion.div>
      )}

      {/* Document Visualization Modal */}
      <DocumentVisualization
        documentId={visualizationModal.documentId}
        filename={visualizationModal.filename}
        isOpen={visualizationModal.isOpen}
        onClose={closeVisualizationModal}
        visualizationType={visualizationType}
      />
    </div>
  )
}

export default Results
