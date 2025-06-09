import { FileUpload, ProcessedDocument, DocumentSummary, ProcessingBatch, ProcessingStatus, ValidationError } from '../types'

export const generateMockFileUpload = (filename: string, index: number): FileUpload => ({
  id: `demo-${Date.now()}-${index}`,
  filename,
  size: Math.floor(Math.random() * 2000000) + 100000, // 100KB to 2MB
  content_type: filename.endsWith('.pdf') ? 'application/pdf' : 'image/jpeg',
  upload_timestamp: new Date().toISOString()
})

export const generateMockProcessedDocument = (fileUpload: FileUpload): ProcessedDocument => {
  const documentTypes = ['1099-INT', '1099-DIV', '1099-G', 'W-2', 'K-1', '1040', 'Schedule C']
  const categories = ['Income Documents', 'Investment Documents', 'Tax Forms', 'Business Documents']
  
  const docType = documentTypes[Math.floor(Math.random() * documentTypes.length)]
  const category = categories[Math.floor(Math.random() * categories.length)]
  
  return {
    id: `processed-${fileUpload.id}`,
    file_upload: fileUpload,
    processing_status: ProcessingStatus.COMPLETED,
    processing_start_time: new Date(Date.now() - Math.random() * 60000).toISOString(),
    processing_end_time: new Date().toISOString(),
    azure_result: {
      doc_type: docType,
      confidence: 0.85 + Math.random() * 0.14, // 85-99% confidence
      fields: generateMockFields(docType),
      page_numbers: [1],
      processing_time: Math.random() * 30 + 10, // 10-40 seconds
      raw_response: {}
    },
    gemini_result: {
      document_category: category,
      document_analysis_summary: `This is a ${docType} document containing ${Object.keys(generateMockFields(docType)).length} key fields. The document appears to be in good condition with clear text and proper formatting.`,
      extracted_key_info: generateMockKeyInfo(docType),
      suggested_bookmark_structure: {
        level1: category,
        level2: docType,
        level3: `${docType} - ${generateMockEntity(docType)}`
      },
      raw_response: {},
      processing_time: Math.random() * 20 + 5 // 5-25 seconds
    },
    validation_errors: Math.random() > 0.8 ? [{
      field: 'date_format',
      message: 'Date format validation warning',
      severity: 'warning' as const
    }] : [],
    created_at: new Date().toISOString()
  }
}

const generateMockFields = (docType: string): Record<string, any> => {
  const baseFields = {
    'document_type': docType,
    'tax_year': '2023',
    'date_issued': '2024-01-31'
  }

  switch (docType) {
    case '1099-INT':
      return {
        ...baseFields,
        'payer_name': 'Demo Bank Corp',
        'payer_tin': '12-3456789',
        'recipient_name': 'John Doe',
        'recipient_ssn': 'XXX-XX-1234',
        'interest_income': (Math.random() * 5000 + 100).toFixed(2),
        'federal_tax_withheld': (Math.random() * 500).toFixed(2)
      }
    case '1099-DIV':
      return {
        ...baseFields,
        'payer_name': 'Investment Corp',
        'payer_tin': '98-7654321',
        'recipient_name': 'Jane Smith',
        'recipient_ssn': 'XXX-XX-5678',
        'ordinary_dividends': (Math.random() * 3000 + 200).toFixed(2),
        'qualified_dividends': (Math.random() * 2000 + 100).toFixed(2)
      }
    case 'W-2':
      return {
        ...baseFields,
        'employer_name': 'Tech Solutions Inc',
        'employer_ein': '45-6789012',
        'employee_name': 'Alex Johnson',
        'employee_ssn': 'XXX-XX-9012',
        'wages': (Math.random() * 80000 + 40000).toFixed(2),
        'federal_tax_withheld': (Math.random() * 15000 + 5000).toFixed(2),
        'social_security_wages': (Math.random() * 80000 + 40000).toFixed(2)
      }
    default:
      return {
        ...baseFields,
        'amount': (Math.random() * 10000 + 500).toFixed(2),
        'description': `Sample ${docType} document`
      }
  }
}

const generateMockKeyInfo = (docType: string): Record<string, any> => {
  return {
    'document_quality': 'High',
    'text_clarity': 'Excellent',
    'completeness_score': Math.floor(Math.random() * 20 + 80), // 80-100%
    'processing_notes': `Successfully processed ${docType} with high confidence`
  }
}

const generateMockEntity = (docType: string): string => {
  const entities = {
    '1099-INT': ['Demo Bank Corp', 'First National Bank', 'Community Credit Union'],
    '1099-DIV': ['Investment Corp', 'Mutual Fund Co', 'Dividend Holdings LLC'],
    'W-2': ['Tech Solutions Inc', 'Global Corp', 'Local Business LLC'],
    '1099-G': ['State of California', 'State of Texas', 'State of New York']
  }
  
  const entityList = entities[docType as keyof typeof entities] || ['Generic Entity']
  return entityList[Math.floor(Math.random() * entityList.length)]
}

export const generateMockBatch = (documents: ProcessedDocument[]): ProcessingBatch => ({
  id: `batch-${Date.now()}`,
  total_documents: documents.length,
  processed_documents: documents.filter(d => d.processing_status === ProcessingStatus.COMPLETED).length,
  failed_documents: documents.filter(d => d.processing_status === ProcessingStatus.ERROR).length,
  status: ProcessingStatus.COMPLETED,
  documents,
  created_at: new Date(Date.now() - 300000).toISOString(), // 5 minutes ago
  completed_at: new Date().toISOString()
})

export const generateDemoDocumentSummaries = (count: number = 5): DocumentSummary[] => {
  const mockFiles = [
    'TAX-1099-INT-2023.pdf',
    'TAX-1099-DIV-Investment.pdf',
    'TAX-W2-TechCorp.pdf',
    'TAX-1099-G-State.pdf',
    'TAX-Schedule-C-Business.pdf'
  ].slice(0, count)

  return mockFiles.map((filename, index) => {
    const fileUpload = generateMockFileUpload(filename, index)
    const processedDoc = generateMockProcessedDocument(fileUpload)
    
    return {
      filename: fileUpload.filename,
      status: processedDoc.processing_status,
      processing_time: processedDoc.processing_end_time && processedDoc.processing_start_time ? 
        (new Date(processedDoc.processing_end_time).getTime() - new Date(processedDoc.processing_start_time).getTime()) / 1000 : 0,
      document_type: processedDoc.azure_result?.doc_type,
      confidence: processedDoc.azure_result?.confidence || 0,
      category: processedDoc.gemini_result?.document_category,
      key_fields: {
        ...processedDoc.azure_result?.fields,
        ...processedDoc.gemini_result?.extracted_key_info
      },
      validation_issues: processedDoc.validation_errors.length,
      analysis_summary: processedDoc.gemini_result?.document_analysis_summary,
      bookmark_path: processedDoc.gemini_result?.suggested_bookmark_structure ? 
        `${processedDoc.gemini_result.suggested_bookmark_structure.level1} > ${processedDoc.gemini_result.suggested_bookmark_structure.level2} > ${processedDoc.gemini_result.suggested_bookmark_structure.level3}` : undefined
    }
  })
}

export const DEMO_FILES = [
  'TAX-1099-INT-2023.pdf',
  'TAX-1099-DIV-Investment.pdf',
  'TAX-W2-TechCorp.pdf',
  'TAX-1099-G-State.pdf',
  'TAX-Schedule-C-Business.pdf',
  'TAX-1040-MainForm.pdf',
  'TAX-K1-Partnership.pdf',
  'TAX-Receipt-Charity.jpg'
]