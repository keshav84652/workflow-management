import React from 'react'
import { Link } from 'react-router-dom'
import {
  Upload,
  Zap,
  FileText,
  BarChart3,
  ArrowRight,
  CheckCircle,
  Clock,
  AlertCircle,
  TrendingUp,
  Building2,
  Sparkles,
  PlayCircle,
  Download,
  FileCheck,
  ChevronRight,
  Info,
  Trash2
} from 'lucide-react'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { useWorkflowState } from '../hooks/useUtils'
import { useProcessingStats } from '../hooks/useApi'
import { useAppStore } from '../store'

const Dashboard: React.FC = () => {
  const clearSession = useAppStore(state => state.clearSession)
  
  const {
    currentStep,
    nextAction,
    workflowProgress,
    hasUploadedFiles,
    hasProcessedDocuments,
    isProcessing,
    currentBatch,
    workpaperMetadata
  } = useWorkflowState()

  const { data: stats, isLoading: statsLoading } = useProcessingStats()
  const uploadedFiles = useAppStore(state => state.uploadedFiles)
  const processedDocuments = useAppStore(state => state.processedDocuments)

  // Enhanced stats with real data
  const enhancedStats = {
    totalDocuments: stats?.total_documents || processedDocuments.length,
    processedToday: stats?.processed_today || 0,
    successRate: stats?.success_rate || (processedDocuments.length > 0 ?
      Math.round((processedDocuments.filter(d => d.processing_status === 'completed').length / processedDocuments.length) * 100) : 0),
    avgProcessingTime: stats?.avg_processing_time || 0
  }

  // Clear session handler
  const handleClearSession = () => {
    if (window.confirm('Are you sure you want to clear all data and start a new session? This will remove all uploaded files, processing results, and workpaper data.')) {
      clearSession()
      toast.success('Session cleared successfully')
    }
  }

  // Workflow steps for progress indicator
  const workflowSteps = [
    { key: 'upload', title: 'Upload', icon: Upload, completed: hasUploadedFiles },
    { key: 'process', title: 'Process', icon: Zap, completed: hasProcessedDocuments },
    { key: 'results', title: 'Review', icon: BarChart3, completed: hasProcessedDocuments },
    { key: 'workpaper', title: 'Generate', icon: FileText, completed: !!workpaperMetadata }
  ]

  // Dynamic quick actions based on current state
  const getQuickActions = () => {
    switch (currentStep) {
      case 'upload_needed':
        return [
          {
            title: 'Upload Documents',
            description: 'Start by uploading your tax documents',
            icon: Upload,
            href: '/upload',
            color: 'bg-primary-500',
            priority: 'high',
            badge: 'Start Here'
          }
        ]
      
      case 'ready_to_process':
        return [
          {
            title: 'Process Documents',
            description: `Process ${uploadedFiles.length} uploaded document${uploadedFiles.length !== 1 ? 's' : ''}`,
            icon: Zap,
            href: '/process',
            color: 'bg-warning-500',
            priority: 'high',
            badge: 'Next Step'
          },
          {
            title: 'Upload More',
            description: 'Add more documents to this batch',
            icon: Upload,
            href: '/upload',
            color: 'bg-gray-500',
            priority: 'low'
          }
        ]
      
      case 'processing':
        return [
          {
            title: 'View Processing',
            description: 'Monitor real-time processing progress',
            icon: Clock,
            href: '/process',
            color: 'bg-blue-500',
            priority: 'high',
            badge: 'In Progress'
          }
        ]
      
      case 'results_ready':
        return [
          {
            title: 'Review Results',
            description: `Review ${processedDocuments.length} processed document${processedDocuments.length !== 1 ? 's' : ''}`,
            icon: BarChart3,
            href: '/results',
            color: 'bg-success-500',
            priority: 'high',
            badge: 'Ready'
          },
          {
            title: 'Generate Workpaper',
            description: 'Create professional PDF workpaper',
            icon: FileText,
            href: '/workpaper',
            color: 'bg-purple-500',
            priority: 'medium'
          }
        ]
      
      case 'workpaper_ready':
        return [
          {
            title: 'Download Workpaper',
            description: 'Download your professional workpaper',
            icon: Download,
            href: '/workpaper',
            color: 'bg-green-500',
            priority: 'high',
            badge: 'Complete'
          },
          {
            title: 'Review Results',
            description: 'Export or review document data',
            icon: BarChart3,
            href: '/results',
            color: 'bg-success-500',
            priority: 'medium'
          }
        ]
      
      default:
        return [
          {
            title: 'Upload Documents',
            description: 'Upload tax documents for AI-powered processing',
            icon: Upload,
            href: '/upload',
            color: 'bg-primary-500',
            priority: 'high'
          }
        ]
    }
  }

  const quickActions = getQuickActions()

  const aiFeatures = [
    {
      title: 'Azure Document Intelligence',
      description: 'OCR and structured data extraction using prebuilt tax models',
      icon: Building2,
      status: 'Ready'
    },
    {
      title: 'Google Gemini AI',
      description: 'Advanced document analysis and categorization',
      icon: Sparkles,
      status: 'Ready'
    },
    {
      title: 'Comprehensive Extraction',
      description: '70+ fields extracted per document with professional accuracy',
      icon: TrendingUp,
      status: 'Enhanced'
    }
  ]

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <motion.h1
              className="text-3xl font-bold text-gray-900 mb-2"
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              Welcome to CPA Copilot
            </motion.h1>
            <motion.p
              className="text-lg text-gray-600"
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
            >
              Your AI-powered tax document processing assistant
            </motion.p>
          </div>
          
          {/* Session Controls */}
          {(hasUploadedFiles || hasProcessedDocuments) && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
              <button
                onClick={handleClearSession}
                className="btn btn-secondary btn-sm"
                title="Clear all data and start a new session"
              >
                <Trash2 className="h-4 w-4 mr-1" />
                New Session
              </button>
            </motion.div>
          )}
        </div>
      </div>

      {/* Workflow Progress */}
      <motion.div 
        className="card mb-8"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
      >
        <div className="card-header">
          <h3 className="text-lg font-semibold text-gray-900">Workflow Progress</h3>
          <p className="text-sm text-gray-600 mt-1">
            Current step: <span className="font-medium capitalize">{currentStep.replace('_', ' ')}</span>
          </p>
        </div>
        <div className="card-body">
          <div className="flex items-center justify-between mb-6">
            {workflowSteps.map((step, index) => {
              const Icon = step.icon
              const isActive = index <= workflowSteps.findIndex(s => s.key === currentStep.split('_')[0])
              const isCompleted = step.completed
              
              return (
                <div key={step.key} className="flex items-center">
                  <div className={`
                    flex items-center justify-center w-10 h-10 rounded-full border-2 transition-all
                    ${isCompleted ? 'bg-success-500 border-success-500 text-white' :
                      isActive ? 'bg-primary-500 border-primary-500 text-white' :
                      'bg-gray-100 border-gray-300 text-gray-400'}
                  `}>
                    {isCompleted ? (
                      <CheckCircle className="h-5 w-5" />
                    ) : (
                      <Icon className="h-5 w-5" />
                    )}
                  </div>
                  <div className="ml-3">
                    <p className={`text-sm font-medium ${isActive ? 'text-gray-900' : 'text-gray-500'}`}>
                      {step.title}
                    </p>
                  </div>
                  {index < workflowSteps.length - 1 && (
                    <div className={`
                      w-8 h-0.5 mx-4 transition-all
                      ${isCompleted ? 'bg-success-300' : 'bg-gray-200'}
                    `} />
                  )}
                </div>
              )
            })}
          </div>

          {/* Progress Bar */}
          <div className="progress-bar">
            <motion.div
              className="progress-fill"
              initial={{ width: 0 }}
              animate={{ width: `${workflowProgress}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>
          <div className="flex justify-between text-sm text-gray-600 mt-2">
            <span>Progress</span>
            <span>{workflowProgress}% Complete</span>
          </div>
        </div>
      </motion.div>

      {/* Stats Cards */}
      <motion.div 
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.3 }}
      >
        <div className="card">
          <div className="card-body">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <FileText className="h-8 w-8 text-primary-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">Total Documents</p>
                <p className="text-2xl font-bold text-gray-900">
                  {statsLoading ? '...' : enhancedStats.totalDocuments}
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-body">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <Clock className="h-8 w-8 text-warning-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">Processed Today</p>
                <p className="text-2xl font-bold text-gray-900">
                  {statsLoading ? '...' : enhancedStats.processedToday}
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-body">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <CheckCircle className="h-8 w-8 text-success-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">Success Rate</p>
                <p className="text-2xl font-bold text-gray-900">
                  {statsLoading ? '...' : `${enhancedStats.successRate}%`}
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-body">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <TrendingUp className="h-8 w-8 text-purple-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">Avg Time</p>
                <p className="text-2xl font-bold text-gray-900">
                  {statsLoading ? '...' : `${enhancedStats.avgProcessingTime.toFixed(1)}s`}
                </p>
              </div>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Current Status & Next Actions */}
      <motion.div 
        className="mb-8"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.4 }}
      >
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Next Steps</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {quickActions.map((action, index) => {
            const Icon = action.icon
            return (
              <motion.div
                key={action.title}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.5 + index * 0.1 }}
              >
                <Link
                  to={action.href}
                  className={`
                    card group hover:shadow-lg transition-all duration-200 block relative
                    ${action.priority === 'high' ? 'ring-2 ring-primary-200' : ''}
                  `}
                >
                  {action.badge && (
                    <div className="absolute -top-2 -right-2 bg-primary-600 text-white text-xs px-2 py-1 rounded-full font-medium">
                      {action.badge}
                    </div>
                  )}
                  <div className="card-body">
                    <div className={`inline-flex p-3 rounded-lg ${action.color} text-white mb-4 group-hover:scale-110 transition-transform duration-200`}>
                      <Icon className="h-6 w-6" />
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">{action.title}</h3>
                    <p className="text-sm text-gray-600 mb-4">{action.description}</p>
                    <div className="flex items-center text-primary-600 font-medium text-sm group-hover:text-primary-700">
                      {action.priority === 'high' ? 'Continue' : 'Go to'}
                      <ArrowRight className="ml-1 h-4 w-4 transition-transform duration-200 group-hover:translate-x-1" />
                    </div>
                  </div>
                </Link>
              </motion.div>
            )
          })}
        </div>
      </motion.div>

      {/* Current Batch Info (if processing or has results) */}
      {(currentBatch || processedDocuments.length > 0) && (
        <motion.div 
          className="card mb-8"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.6 }}
        >
          <div className="card-header">
            <h3 className="text-lg font-semibold text-gray-900">Current Batch Status</h3>
          </div>
          <div className="card-body">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center">
                <FileText className="h-8 w-8 text-primary-600 mx-auto mb-2" />
                <p className="text-2xl font-bold text-gray-900">
                  {currentBatch?.total_documents || processedDocuments.length}
                </p>
                <p className="text-sm text-gray-600">Total Documents</p>
              </div>
              <div className="text-center">
                <CheckCircle className="h-8 w-8 text-success-600 mx-auto mb-2" />
                <p className="text-2xl font-bold text-gray-900">
                  {currentBatch?.processed_documents || processedDocuments.filter(d => d.processing_status === 'completed').length}
                </p>
                <p className="text-sm text-gray-600">Completed</p>
              </div>
              <div className="text-center">
                {isProcessing ? (
                  <Clock className="h-8 w-8 text-warning-600 mx-auto mb-2 animate-pulse" />
                ) : (
                  <TrendingUp className="h-8 w-8 text-purple-600 mx-auto mb-2" />
                )}
                <p className="text-2xl font-bold text-gray-900">
                  {isProcessing ? 'Processing...' : 'Complete'}
                </p>
                <p className="text-sm text-gray-600">Status</p>
              </div>
            </div>
            
            {currentBatch && (
              <div className="mt-4 text-center">
                <Link 
                  to={isProcessing ? '/process' : '/results'}
                  className="btn btn-primary"
                >
                  {isProcessing ? 'View Progress' : 'View Results'}
                  <ChevronRight className="ml-1 h-4 w-4" />
                </Link>
              </div>
            )}
          </div>
        </motion.div>
      )}

      {/* AI Features Overview */}
      <motion.div 
        className="card mb-8"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.7 }}
      >
        <div className="card-header">
          <h2 className="text-xl font-semibold text-gray-900">AI-Powered Features</h2>
          <p className="text-sm text-gray-600 mt-1">Advanced document processing capabilities</p>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {aiFeatures.map((feature, index) => {
              const Icon = feature.icon
              return (
                <div key={feature.title} className="flex items-start">
                  <div className="flex-shrink-0">
                    <div className="flex items-center justify-center h-10 w-10 rounded-lg bg-primary-100">
                      <Icon className="h-6 w-6 text-primary-600" />
                    </div>
                  </div>
                  <div className="ml-4">
                    <div className="flex items-center mb-1">
                      <h3 className="text-lg font-medium text-gray-900">{feature.title}</h3>
                      <span className="ml-2 badge badge-success">{feature.status}</span>
                    </div>
                    <p className="text-sm text-gray-600">{feature.description}</p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </motion.div>

      {/* Getting Started Guide (only show when starting fresh) */}
      {currentStep === 'upload_needed' && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.8 }}
        >
          <div className="card bg-gradient-to-r from-primary-50 to-primary-100 border-primary-200">
            <div className="card-body">
              <div className="flex items-start">
                <div className="flex-shrink-0">
                  <Info className="h-6 w-6 text-primary-600" />
                </div>
                <div className="ml-4">
                  <h3 className="text-lg font-semibold text-primary-900 mb-2">Ready to get started?</h3>
                  <p className="text-primary-700 mb-4">
                    Upload your tax documents and experience the power of AI-driven analysis.
                    Get comprehensive data extraction, professional categorization, and automated workpaper generation.
                  </p>
                  <div className="bg-white/50 rounded-lg p-4 mb-4">
                    <h4 className="font-medium text-primary-900 mb-2">3-Step Workflow:</h4>
                    <ol className="text-sm text-primary-800 space-y-1">
                      <li>1. <strong>Upload</strong> - Add your tax documents (PDF, JPG, PNG, TIFF)</li>
                      <li>2. <strong>Process</strong> - AI analyzes and extracts data automatically</li>
                      <li>3. <strong>Generate</strong> - Create professional workpapers with bookmarks</li>
                    </ol>
                  </div>
                  <div className="flex space-x-4">
                    <Link to="/upload" className="btn btn-primary">
                      <Upload className="h-4 w-4 mr-2" />
                      Start Upload
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  )
}

export default Dashboard
