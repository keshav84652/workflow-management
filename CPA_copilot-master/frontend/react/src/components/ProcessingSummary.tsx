import React from 'react'
import { motion } from 'framer-motion'
import {
  FileText,
  CheckCircle,
  AlertCircle,
  Clock,
  TrendingUp,
  BarChart3,
  PieChart,
  Building2,
  Sparkles
} from 'lucide-react'
import { ProcessedDocument, DocumentSummary } from '../types'

interface ProcessingSummaryProps {
  documents: DocumentSummary[] | ProcessedDocument[]
  title?: string
  showCharts?: boolean
  className?: string
}

const ProcessingSummary: React.FC<ProcessingSummaryProps> = ({
  documents,
  title = "Processing Summary",
  showCharts = true,
  className = ""
}) => {
  // Convert ProcessedDocument to DocumentSummary if needed
  const summaryDocuments: DocumentSummary[] = documents.map(doc => {
    if ('file_upload' in doc) {
      // This is a ProcessedDocument
      return {
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
      }
    }
    return doc as DocumentSummary
  })

  // Calculate statistics
  const stats = {
    total: summaryDocuments.length,
    completed: summaryDocuments.filter(d => d.status === 'completed').length,
    failed: summaryDocuments.filter(d => d.status === 'error').length,
    processing: summaryDocuments.filter(d => d.status === 'processing').length,
    avgProcessingTime: summaryDocuments.reduce((sum, d) => sum + (d.processing_time || 0), 0) / summaryDocuments.length || 0,
    totalValidationIssues: summaryDocuments.reduce((sum, d) => sum + d.validation_issues, 0),
    avgConfidence: summaryDocuments.reduce((sum, d) => sum + (d.confidence || 0), 0) / summaryDocuments.length || 0
  }

  // Category breakdown
  const categoryStats = summaryDocuments.reduce((acc, doc) => {
    const category = doc.category || 'Unknown'
    acc[category] = (acc[category] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  // Document type breakdown
  const typeStats = summaryDocuments.reduce((acc, doc) => {
    const type = doc.document_type || 'Unknown'
    acc[type] = (acc[type] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  const formatTime = (seconds: number) => {
    if (seconds < 60) return `${seconds.toFixed(1)}s`
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}m ${remainingSeconds.toFixed(0)}s`
  }

  const getSuccessRate = () => {
    if (stats.total === 0) return 0
    return Math.round((stats.completed / stats.total) * 100)
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
        <div className="flex items-center space-x-2 text-sm text-gray-600">
          <BarChart3 className="h-4 w-4" />
          <span>{stats.total} documents analyzed</span>
        </div>
      </div>

      {/* Main Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="card"
        >
          <div className="card-body text-center">
            <FileText className="h-8 w-8 text-primary-600 mx-auto mb-2" />
            <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
            <p className="text-sm text-gray-600">Total Documents</p>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
          className="card"
        >
          <div className="card-body text-center">
            <CheckCircle className="h-8 w-8 text-success-600 mx-auto mb-2" />
            <p className="text-2xl font-bold text-gray-900">{stats.completed}</p>
            <p className="text-sm text-gray-600">Completed</p>
            <p className="text-xs text-success-600 font-medium">{getSuccessRate()}% success rate</p>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.2 }}
          className="card"
        >
          <div className="card-body text-center">
            <Clock className="h-8 w-8 text-warning-600 mx-auto mb-2" />
            <p className="text-2xl font-bold text-gray-900">{formatTime(stats.avgProcessingTime)}</p>
            <p className="text-sm text-gray-600">Avg Processing Time</p>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.3 }}
          className="card"
        >
          <div className="card-body text-center">
            <TrendingUp className="h-8 w-8 text-purple-600 mx-auto mb-2" />
            <p className="text-2xl font-bold text-gray-900">{(stats.avgConfidence * 100).toFixed(0)}%</p>
            <p className="text-sm text-gray-600">Avg Confidence</p>
          </div>
        </motion.div>
      </div>

      {/* Detailed Breakdown */}
      {showCharts && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Categories */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.4 }}
            className="card"
          >
            <div className="card-header">
              <div className="flex items-center">
                <Sparkles className="h-5 w-5 text-purple-600 mr-2" />
                <h4 className="font-medium text-gray-900">Document Categories</h4>
              </div>
            </div>
            <div className="card-body">
              <div className="space-y-3">
                {Object.entries(categoryStats).map(([category, count]) => {
                  const percentage = (count / stats.total) * 100
                  return (
                    <div key={category} className="flex items-center justify-between">
                      <span className="text-sm text-gray-700">{category}</span>
                      <div className="flex items-center space-x-2">
                        <div className="w-20 bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-purple-600 h-2 rounded-full"
                            style={{ width: `${percentage}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium text-gray-900 w-8">{count}</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </motion.div>

          {/* Document Types */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.5 }}
            className="card"
          >
            <div className="card-header">
              <div className="flex items-center">
                <Building2 className="h-5 w-5 text-blue-600 mr-2" />
                <h4 className="font-medium text-gray-900">Document Types</h4>
              </div>
            </div>
            <div className="card-body">
              <div className="space-y-3">
                {Object.entries(typeStats).slice(0, 5).map(([type, count]) => {
                  const percentage = (count / stats.total) * 100
                  return (
                    <div key={type} className="flex items-center justify-between">
                      <span className="text-sm text-gray-700 truncate">{type}</span>
                      <div className="flex items-center space-x-2">
                        <div className="w-20 bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full"
                            style={{ width: `${percentage}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium text-gray-900 w-8">{count}</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </motion.div>
        </div>
      )}

      {/* Status Summary */}
      {(stats.failed > 0 || stats.totalValidationIssues > 0) && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.6 }}
          className="card bg-warning-50 border-warning-200"
        >
          <div className="card-body">
            <div className="flex items-start">
              <AlertCircle className="h-5 w-5 text-warning-600 mt-0.5 mr-3" />
              <div>
                <h4 className="font-medium text-warning-900 mb-1">Processing Issues</h4>
                <div className="text-sm text-warning-800 space-y-1">
                  {stats.failed > 0 && (
                    <p>• {stats.failed} document{stats.failed !== 1 ? 's' : ''} failed to process</p>
                  )}
                  {stats.totalValidationIssues > 0 && (
                    <p>• {stats.totalValidationIssues} validation issue{stats.totalValidationIssues !== 1 ? 's' : ''} found</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  )
}

export default ProcessingSummary