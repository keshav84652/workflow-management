"""
Income Worksheet Generation Service
Generates CSV-formatted income worksheets from tax documents using Gemini AI
"""

import asyncio
import json
import csv
import io
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .gemini_service import GeminiDocumentService
from ..models.document import FileUpload


class IncomeWorksheetService:
    """Service for generating income worksheets from tax documents"""
    
    # CSV Extraction Prompt for Gemini
    CSV_EXTRACTION_PROMPT = """
You are a tax data extractor that outputs **CSV-formatted tables** for CPA income worksheets.

Extract data from tax documents and format as CSV with these specific columns for each form type:

**CRITICAL CSV RULES:**
- NO commas in field descriptions (use parentheses instead)
- Only include the most important fields for each form type
- Each section: Header row → Column headers → Data rows → Subtotal row
- Leave empty cells blank (no dashes or N/A)

**Form-specific columns:**

**W-2:**
`Document,Box 1 Wages,Box 2 Fed Tax,Box 17 State Tax,Box 12 Codes,Notes`

**1099-G:**
`Document,Box 1 Unemployment,Box 2 State Refunds,Box 4 Fed Tax Withheld,Notes`

**1099-INT:**
`Document,Box 1 Interest Income,Notes`

**1099-DIV:**
`Document,Box 1a Ordinary Div,Box 1b Qualified Div,Notes`

**1099-B:**
`Document,Box 1d Proceeds,Box 1e Cost Basis,Box 1g Wash Sale Loss,Notes`

**1099-R:**
`Document,Box 1 Gross Distribution,Box 2a Taxable Amount,Box 4 Fed Tax Withheld,Notes`

**K-1 (1065):**
`Document,Box 1 Ordinary Inc,Box 2 Rental Income,Box 5 Interest,Box 14 Self Emp Earnings,Notes`

**Schedule E (Rental):**
`Document,Rental Income,Expenses,Net Income,Notes`

**Format Example:**
```
W-2,,,,
Document,Box 1 Wages,Box 2 Fed Tax,Box 17 State Tax,Box 12 Codes,Notes
W-2 John Doe,50000,6000,1200,D=2400,Primary taxpayer
Subtotal,50000,6000,1200,,

1099-G,,,
Document,Box 1 Unemployment,Box 2 State Refunds,Box 4 Fed Tax Withheld,Notes
1099-G John Doe,5000,1200,600,State unemployment
Subtotal,5000,1200,600,
```

Extract data from the provided document(s) using this exact format. Output only CSV data.
"""
    
    def __init__(self):
        """Initialize the income worksheet service"""
        self.gemini_service = GeminiDocumentService()
    
    async def generate_income_worksheet(self, documents: List[FileUpload], client_name: str = "Client") -> Dict[str, Any]:
        """
        Generate income worksheet from a list of tax documents
        
        Args:
            documents: List of FileUpload objects containing tax documents
            client_name: Name of the client for the worksheet
            
        Returns:
            Dictionary with CSV content and metadata
        """
        try:
            if not documents:
                return {
                    'success': False,
                    'error': 'No documents provided',
                    'csv_content': '',
                    'filename': f'{client_name}_income_worksheet.csv'
                }
            
            # Process all documents with Gemini using the CSV extraction prompt
            csv_content = await self._extract_csv_from_documents(documents)
            
            if not csv_content or csv_content.strip() == "":
                return {
                    'success': False,
                    'error': 'No tax data could be extracted from documents',
                    'csv_content': '',
                    'filename': f'{client_name}_income_worksheet.csv'
                }
            
            # Add header with client name and generation timestamp
            header_content = self._generate_worksheet_header(client_name, len(documents))
            full_csv_content = header_content + "\n" + csv_content
            
            # Validate CSV format
            validation_result = self._validate_csv_content(full_csv_content)
            
            return {
                'success': True,
                'csv_content': full_csv_content,
                'filename': f'{client_name.replace(" ", "_")}_income_worksheet_{datetime.now().strftime("%Y%m%d")}.csv',
                'document_count': len(documents),
                'validation': validation_result,
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Income worksheet generation failed: {str(e)}',
                'csv_content': '',
                'filename': f'{client_name}_income_worksheet.csv'
            }
    
    async def _extract_csv_from_documents(self, documents: List[FileUpload]) -> str:
        """Extract CSV data from documents using Gemini AI"""
        try:
            # Multi-document processing - process each document and combine
            all_csv_parts = []
            
            for doc in documents:
                # Read file content
                if not doc.file_path or not doc.file_path.exists():
                    print(f"File not found: {doc.file_path}")
                    continue
                
                with open(doc.file_path, 'rb') as f:
                    document_content = f.read()
                
                # Call Gemini with custom prompt (not async - Gemini service is sync)
                result = self.gemini_service.analyze_document(
                    document_content=document_content,
                    document_name=doc.filename,
                    content_type=doc.content_type,
                    custom_prompt=self.CSV_EXTRACTION_PROMPT
                )
                
                if result and hasattr(result, 'raw_response'):
                    # Extract CSV content from the custom response structure
                    if isinstance(result.raw_response, dict) and 'csv_output' in result.raw_response:
                        csv_content = result.raw_response['csv_output']
                    else:
                        csv_content = str(result.raw_response)
                    
                    csv_part = self._clean_csv_response(csv_content)
                    if csv_part.strip():
                        all_csv_parts.append(csv_part)
            
            # Combine all CSV parts
            if all_csv_parts:
                return self._combine_csv_parts(all_csv_parts)
            
            return ""
            
        except Exception as e:
            print(f"Error extracting CSV from documents: {e}")
            return ""
    
    def _clean_csv_response(self, response: str) -> str:
        """Clean Gemini response to extract pure CSV content"""
        if not response:
            return ""
        
        # Remove markdown code blocks if present
        response = response.replace("```csv", "").replace("```", "").replace("```\n", "").replace("\n```", "")
        
        # Remove any leading/trailing explanatory text
        lines = response.split('\n')
        csv_lines = []
        current_section = None
        seen_sections = set()
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if this is a section header (form type)
            if self._is_section_header(line):
                section_type = line.split(',')[0].upper()
                
                # Skip duplicate sections
                if section_type in seen_sections:
                    current_section = None
                    continue
                    
                seen_sections.add(section_type)
                current_section = section_type
                csv_lines.append(line)
                
            elif current_section and (',' in line):
                # This is a data line for the current section
                csv_lines.append(line)
        
        return '\n'.join(csv_lines)
    
    def _is_section_header(self, line: str) -> bool:
        """Check if a line is a section header (form type)"""
        if not line or ',' not in line:
            return False
            
        fields = line.split(',')
        first_field = fields[0].strip().upper()
        
        # Section headers should have mostly empty fields after the form type
        # Count non-empty fields after the first one
        non_empty_after_first = sum(1 for field in fields[1:] if field.strip())
        
        # If there are many non-empty fields, it's likely a data row
        if non_empty_after_first > 2:
            return False
        
        # Check for common patterns in section headers
        form_patterns = [
            'W-2', '1099-G', '1099-INT', '1099-DIV', '1099-B', '1099-R', 
            '1099-MISC', '1099-NEC', 'K-1', 'SCHEDULE E', 'SCHEDULE K-1'
        ]
        
        # Section header should start with a form pattern and not contain personal names
        for pattern in form_patterns:
            if first_field == pattern or first_field.startswith(pattern + ' (') or first_field.startswith(pattern + '('):
                # Additional check: should not contain common name patterns
                name_indicators = ['JOHN', 'JANE', 'SMITH', 'DOE', 'INC', 'LLC', 'CORP']
                if not any(indicator in first_field for indicator in name_indicators):
                    return True
        
        return False
    
    def _combine_csv_parts(self, csv_parts: List[str]) -> str:
        """Combine multiple CSV parts, merging sections by document type"""
        combined_sections = {}
        
        for csv_part in csv_parts:
            sections = self._parse_csv_sections(csv_part)
            
            for section_name, section_data in sections.items():
                if section_name in combined_sections:
                    # Merge sections of same type
                    combined_sections[section_name].extend(section_data)
                else:
                    combined_sections[section_name] = section_data
        
        # Reconstruct CSV from combined sections
        final_csv_lines = []
        
        for section_name, section_data in combined_sections.items():
            final_csv_lines.append(f"{section_name},,,,,")  # Section header
            final_csv_lines.extend(section_data)
            final_csv_lines.append("")  # Empty line between sections
        
        return '\n'.join(final_csv_lines)
    
    def _parse_csv_sections(self, csv_content: str) -> Dict[str, List[str]]:
        """Parse CSV content into sections by document type"""
        sections = {}
        current_section = None
        current_data = []
        
        for line in csv_content.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Check if this is a section header (document type)
            if self._is_section_header(line):
                # Save previous section
                if current_section and current_data:
                    # Ensure we have at least column headers and a data row
                    if len(current_data) >= 2:
                        sections[current_section] = current_data
                
                # Start new section
                current_section = line.split(',')[0]
                current_data = []
            elif current_section and ',' in line:
                current_data.append(line)
        
        # Save last section
        if current_section and current_data and len(current_data) >= 2:
            sections[current_section] = current_data
        
        return sections
    
    def _generate_worksheet_header(self, client_name: str, document_count: int) -> str:
        """Generate header information for the worksheet"""
        timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        
        header = [
            f"Income Worksheet - {client_name}",
            f"Generated: {timestamp}",
            f"Documents Processed: {document_count}",
            f"Generated by: CPA WorkflowPilot AI",
            "",  # Empty line separator
        ]
        
        return '\n'.join(header)
    
    def _validate_csv_content(self, csv_content: str) -> Dict[str, Any]:
        """Validate CSV content and return validation results"""
        try:
            # Try to parse as CSV
            csv_reader = csv.reader(io.StringIO(csv_content))
            rows = list(csv_reader)
            
            return {
                'is_valid': True,
                'row_count': len(rows),
                'has_data': len(rows) > 5,  # More than just header
                'sections_found': self._count_sections(csv_content)
            }
            
        except Exception as e:
            return {
                'is_valid': False,
                'error': str(e),
                'row_count': 0,
                'has_data': False,
                'sections_found': 0
            }
    
    def _count_sections(self, csv_content: str) -> int:
        """Count the number of tax document sections in the CSV"""
        section_count = 0
        for line in csv_content.split('\n'):
            if line.strip().upper().startswith(('W-2', 'K-1', '1099', 'SCHEDULE')):
                section_count += 1
        return section_count