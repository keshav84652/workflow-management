// Application Constants
export const APP_CONFIG = {
  name: 'CPA Copilot',
  version: '1.0.0',
  description: 'AI-powered tax document processing assistant',
} as const

// File Upload Constants
export const FILE_UPLOAD = {
  maxSize: parseInt(import.meta.env.VITE_MAX_FILE_SIZE || '10485760'), // 10MB
  allowedTypes: (import.meta.env.VITE_ALLOWED_FILE_TYPES || 'pdf,jpg,jpeg,png,tiff').split(','),
  maxFiles: 20,
} as const

// API Constants
export const API_CONFIG = {
  baseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 300000, // 5 minutes
  retryAttempts: 3,
} as const

// Processing Status Constants
export const PROCESSING_STATUS = {
  PENDING: 'pending',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  ERROR: 'error',
  CANCELLED: 'cancelled',
} as const

// Document Categories
export const DOCUMENT_CATEGORIES = [
  'Income Documents',
  'Deduction Documents',
  'Investment Documents',
  'Business Documents',
  'Property Documents',
  'Other Tax Documents',
] as const

// Common Form Types
export const FORM_TYPES = [
  'W-2',
  '1099-INT',
  '1099-DIV',
  '1099-G',
  '1099-MISC',
  '1099-NEC',
  '1099-R',
  '1098',
  '1098-E',
  '1098-T',
  'K-1',
  '8949',
  'Schedule C',
  'Schedule D',
  'Other',
] as const

// Export Formats
export const EXPORT_FORMATS = [
  { value: 'json', label: 'JSON', description: 'Structured data format' },
  { value: 'csv', label: 'CSV', description: 'Spreadsheet compatible format' },
  { value: 'pdf', label: 'PDF', description: 'Consolidated workpaper' },
] as const

// Toast Configuration
export const TOAST_CONFIG = {
  duration: 4000,
  position: 'top-right' as const,
  style: {
    borderRadius: '8px',
    background: '#1f2937',
    color: '#f3f4f6',
  },
} as const

// Color Schemes for Charts
export const CHART_COLORS = [
  '#3b82f6', // blue-500
  '#10b981', // emerald-500
  '#f59e0b', // amber-500
  '#ef4444', // red-500
  '#8b5cf6', // purple-500
  '#06b6d4', // cyan-500
  '#84cc16', // lime-500
  '#f97316', // orange-500
] as const

// Validation Messages
export const VALIDATION_MESSAGES = {
  required: 'This field is required',
  fileSize: `File size must be less than ${FILE_UPLOAD.maxSize / 1024 / 1024}MB`,
  fileType: `Only ${FILE_UPLOAD.allowedTypes.join(', ')} files are allowed`,
  maxFiles: `Maximum ${FILE_UPLOAD.maxFiles} files allowed`,
  email: 'Please enter a valid email address',
  minLength: (min: number) => `Minimum ${min} characters required`,
  maxLength: (max: number) => `Maximum ${max} characters allowed`,
} as const

// Animation Durations
export const ANIMATION = {
  fast: 150,
  normal: 300,
  slow: 500,
} as const

// Breakpoints (matching Tailwind)
export const BREAKPOINTS = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  '2xl': 1536,
} as const

// Storage Keys
export const STORAGE_KEYS = {
  authToken: 'cpa_copilot_auth_token',
  userPreferences: 'cpa_copilot_preferences',
  processingConfig: 'cpa_copilot_processing_config',
  recentDocuments: 'cpa_copilot_recent_docs',
} as const

// Feature Flags
export const FEATURES = {
  enableDevTools: import.meta.env.VITE_ENABLE_DEV_TOOLS === 'true',
  enableAnalytics: import.meta.env.VITE_ENABLE_ANALYTICS === 'true',
  enableExperimentalFeatures: import.meta.env.VITE_ENABLE_EXPERIMENTAL === 'true',
} as const

// Error Codes
export const ERROR_CODES = {
  NETWORK_ERROR: 'NETWORK_ERROR',
  AUTH_ERROR: 'AUTH_ERROR',
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  FILE_ERROR: 'FILE_ERROR',
  PROCESSING_ERROR: 'PROCESSING_ERROR',
  SERVER_ERROR: 'SERVER_ERROR',
} as const

// Success Messages
export const SUCCESS_MESSAGES = {
  uploadComplete: 'Files uploaded successfully',
  processingComplete: 'Document processing completed',
  workpaperGenerated: 'Workpaper generated successfully',
  exportComplete: 'Data exported successfully',
  settingsSaved: 'Settings saved successfully',
} as const

// Loading Messages
export const LOADING_MESSAGES = {
  uploading: 'Uploading files...',
  processing: 'Processing documents...',
  generating: 'Generating workpaper...',
  exporting: 'Exporting data...',
  loading: 'Loading...',
} as const
