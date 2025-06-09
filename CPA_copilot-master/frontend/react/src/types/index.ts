// Core document processing types
export interface FileUpload {
  id: string;
  filename: string;
  content_type: string;
  size: number;
  file_path?: string;
  upload_timestamp: string;
}

export interface ProcessedDocument {
  id: string;
  file_upload: FileUpload;
  processing_status: ProcessingStatus;
  processing_start_time: string;
  processing_end_time?: string;
  azure_result?: AzureExtractionResult;
  gemini_result?: GeminiAnalysisResult;
  field_comparison?: FieldComparison;
  validation_errors: ValidationError[];
  created_at: string;
}

export interface ProcessingBatch {
  id: string;
  total_documents: number;
  processed_documents: number;
  failed_documents: number;
  status: ProcessingStatus;
  documents: ProcessedDocument[];
  created_at: string;
  completed_at?: string;
  workpaper_metadata?: WorkpaperMetadata;
}

export enum ProcessingStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  PARTIALLY_COMPLETED = 'partially_completed',
  ERROR = 'error',
}

// Azure Document Intelligence types
export interface AzureExtractionResult {
  doc_type: string;
  confidence: number;
  fields: Record<string, any>;
  page_numbers: number[];
  raw_response: Record<string, any>;
  processing_time: number;
}

// Gemini AI types
export interface GeminiAnalysisResult {
  document_category: string;
  document_analysis_summary: string;
  extracted_key_info: ExtractedKeyInfo;
  suggested_bookmark_structure: BookmarkStructure;
  raw_response: Record<string, any>;
  processing_time?: number;
}

export interface ExtractedKeyInfo {
  tax_year?: string;
  form_type?: string;
  payer_name?: string;
  payer_tin?: string;
  payer_address?: string;
  payer_phone?: string;
  recipient_name?: string;
  recipient_tin?: string;
  recipient_address?: string;
  account_number?: string;
  is_corrected_document?: string;
  [key: string]: any; // For comprehensive extraction fields
}

export interface BookmarkStructure {
  level1: string;
  level2: string;
  level3: string;
}

export interface ValidationError {
  field: string;
  message: string;
  severity: 'error' | 'warning' | 'info';
}

export interface FieldComparison {
  matching_fields: Record<string, any>;
  discrepancies: Record<string, { gemini: any; azure: any }>;
  gemini_only_fields: Record<string, any>;
  azure_only_fields: Record<string, any>;
}

// Workpaper generation types
export interface WorkpaperMetadata {
  title: string;
  tax_year?: string;
  preparer_name?: string;
  client_name?: string;
  total_documents: number;
  document_categories: Record<string, number>;
  output_path?: string;
  file_size_bytes?: number;
  page_count?: number;
  generation_date: string;
}

// API response types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

// Processing configuration
export interface ProcessingConfig {
  enable_azure: boolean;
  enable_gemini: boolean;
  pii_mode: 'ignore' | 'mask' | 'remove';
}

// Export formats
export enum ExportFormat {
  JSON = 'json',
  CSV = 'csv',
  EXCEL = 'excel',
}

// UI State types
export interface UploadState {
  files: File[];
  uploading: boolean;
  progress: number;
  error?: string;
}

export interface ProcessingState {
  batch?: ProcessingBatch;
  processing: boolean;
  progress: number;
  error?: string;
}

// Statistics and insights
export interface ProcessingStats {
  total_documents: number;
  successful_documents: number;
  failed_documents: number;
  total_processing_time: number;
  categories: Record<string, number>;
  document_types: Record<string, number>;
}

// Document summary for display
export interface DocumentSummary {
  filename: string;
  status: ProcessingStatus;
  processing_time?: number;
  document_type?: string;
  confidence?: number;
  category?: string;
  key_fields: Record<string, any>;
  validation_issues: number;
  analysis_summary?: string;
  bookmark_path?: string;
}

// Advanced extraction data for comprehensive analysis
export interface DetailedAmounts {
  box_number: string;
  box_description: string;
  amount: string;
}

export interface TaxWithholdings {
  withholding_type: string;
  amount: string;
  box_reference?: string;
}

export interface StateTaxInfo {
  state_abbreviation: string;
  state_id_number?: string;
  state_tax_withheld?: string;
  state_wages?: string;
}

export interface SignificantAmounts {
  description: string;
  amount: string;
  category: 'Income' | 'Withholding' | 'Distribution' | 'Deduction' | 'Other';
}

export interface AdditionalFields {
  foreign_account_indicator?: string;
  backup_withholding?: string;
  investment_expenses?: string;
  cash_liquidation?: string;
  noncash_liquidation?: string;
  federal_tax_withheld?: string;
  section_199a_dividends?: string;
  other_income?: string;
  fatca_filing_requirement?: string;
}

// Comprehensive Gemini extraction
export interface ComprehensiveGeminiResult {
  document_category: string;
  document_analysis_summary: string;
  extracted_key_info: ExtractedKeyInfo;
  detailed_amounts: DetailedAmounts[];
  tax_withholdings: TaxWithholdings[];
  state_tax_info: StateTaxInfo[];
  significant_amounts: SignificantAmounts[];
  additional_fields: AdditionalFields;
  suggested_bookmark_structure: BookmarkStructure;
}
