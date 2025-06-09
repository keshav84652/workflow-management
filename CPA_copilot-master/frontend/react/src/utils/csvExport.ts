import { DocumentSummary } from '../types'

export interface CSVExportOptions {
  includeHeaders?: boolean
  delimiter?: string
  filename?: string
}

export const exportToCSV = (
  data: DocumentSummary[],
  options: CSVExportOptions = {}
) => {
  const {
    includeHeaders = true,
    delimiter = ',',
    filename = `cpa-copilot-results-${new Date().toISOString().split('T')[0]}.csv`
  } = options

  // Define the columns we want to export
  const columns = [
    { key: 'filename', label: 'Filename' },
    { key: 'status', label: 'Status' },
    { key: 'document_type', label: 'Document Type' },
    { key: 'category', label: 'Category' },
    { key: 'confidence', label: 'Confidence' },
    { key: 'processing_time', label: 'Processing Time (s)' },
    { key: 'validation_issues', label: 'Validation Issues' },
    { key: 'analysis_summary', label: 'Analysis Summary' },
    { key: 'bookmark_path', label: 'Bookmark Path' }
  ]

  // Helper function to escape CSV values
  const escapeCSVValue = (value: any): string => {
    if (value === null || value === undefined) return ''
    
    const stringValue = String(value)
    
    // If the value contains delimiter, newlines, or quotes, wrap in quotes and escape internal quotes
    if (stringValue.includes(delimiter) || stringValue.includes('\n') || stringValue.includes('"')) {
      return `"${stringValue.replace(/"/g, '""')}"`
    }
    
    return stringValue
  }

  // Create CSV content
  let csvContent = ''

  // Add headers if requested
  if (includeHeaders) {
    const headers = columns.map(col => escapeCSVValue(col.label)).join(delimiter)
    csvContent += headers + '\n'
  }

  // Add data rows
  data.forEach(item => {
    const row = columns.map(col => {
      let value = (item as any)[col.key]
      
      // Special formatting for specific fields
      if (col.key === 'confidence' && typeof value === 'number') {
        value = `${(value * 100).toFixed(1)}%`
      } else if (col.key === 'processing_time' && typeof value === 'number') {
        value = value.toFixed(2)
      }
      
      return escapeCSVValue(value)
    }).join(delimiter)
    
    csvContent += row + '\n'
  })

  // Create and download the file
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  
  if (link.download !== undefined) {
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', filename)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }
}

export const exportKeyFieldsToCSV = (
  data: DocumentSummary[],
  options: CSVExportOptions = {}
) => {
  const {
    includeHeaders = true,
    delimiter = ',',
    filename = `cpa-copilot-key-fields-${new Date().toISOString().split('T')[0]}.csv`
  } = options

  // Get all unique key fields across all documents
  const allKeyFields = new Set<string>()
  data.forEach(doc => {
    Object.keys(doc.key_fields || {}).forEach(field => allKeyFields.add(field))
  })

  const baseColumns = [
    { key: 'filename', label: 'Filename' },
    { key: 'document_type', label: 'Document Type' },
    { key: 'category', label: 'Category' }
  ]

  const keyFieldColumns = Array.from(allKeyFields).map(field => ({
    key: field,
    label: field
  }))

  const columns = [...baseColumns, ...keyFieldColumns]

  // Helper function to escape CSV values
  const escapeCSVValue = (value: any): string => {
    if (value === null || value === undefined) return ''
    
    const stringValue = String(value)
    
    if (stringValue.includes(delimiter) || stringValue.includes('\n') || stringValue.includes('"')) {
      return `"${stringValue.replace(/"/g, '""')}"`
    }
    
    return stringValue
  }

  // Create CSV content
  let csvContent = ''

  // Add headers
  if (includeHeaders) {
    const headers = columns.map(col => escapeCSVValue(col.label)).join(delimiter)
    csvContent += headers + '\n'
  }

  // Add data rows
  data.forEach(item => {
    const row = columns.map(col => {
      if (baseColumns.some(baseCol => baseCol.key === col.key)) {
        return escapeCSVValue((item as any)[col.key])
      } else {
        // This is a key field
        return escapeCSVValue(item.key_fields?.[col.key])
      }
    }).join(delimiter)
    
    csvContent += row + '\n'
  })

  // Create and download the file
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  
  if (link.download !== undefined) {
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', filename)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }
}

export const exportSummaryToCSV = (
  data: DocumentSummary[],
  options: CSVExportOptions = {}
) => {
  const {
    includeHeaders = true,
    delimiter = ',',
    filename = `cpa-copilot-summary-${new Date().toISOString().split('T')[0]}.csv`
  } = options

  // Create summary data
  const summary = {
    total_documents: data.length,
    successful_documents: data.filter(d => d.status === 'completed').length,
    failed_documents: data.filter(d => d.status === 'error').length,
    avg_processing_time: data.reduce((sum, d) => sum + (d.processing_time || 0), 0) / data.length,
    total_validation_issues: data.reduce((sum, d) => sum + d.validation_issues, 0),
    categories: {} as Record<string, number>,
    document_types: {} as Record<string, number>
  }

  // Count categories and document types
  data.forEach(doc => {
    if (doc.category) {
      summary.categories[doc.category] = (summary.categories[doc.category] || 0) + 1
    }
    if (doc.document_type) {
      summary.document_types[doc.document_type] = (summary.document_types[doc.document_type] || 0) + 1
    }
  })

  // Create CSV content for summary
  let csvContent = ''

  if (includeHeaders) {
    csvContent += 'Metric,Value\n'
  }

  csvContent += `Total Documents,${summary.total_documents}\n`
  csvContent += `Successful Documents,${summary.successful_documents}\n`
  csvContent += `Failed Documents,${summary.failed_documents}\n`
  csvContent += `Average Processing Time,${summary.avg_processing_time.toFixed(2)}s\n`
  csvContent += `Total Validation Issues,${summary.total_validation_issues}\n`
  csvContent += '\n'

  csvContent += 'Categories,Count\n'
  Object.entries(summary.categories).forEach(([category, count]) => {
    csvContent += `${category},${count}\n`
  })
  csvContent += '\n'

  csvContent += 'Document Types,Count\n'
  Object.entries(summary.document_types).forEach(([type, count]) => {
    csvContent += `${type},${count}\n`
  })

  // Create and download the file
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  
  if (link.download !== undefined) {
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', filename)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }
}