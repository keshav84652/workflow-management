"""
Document Analysis Services for CPA WorkflowPilot
Simplified version of the CPA Copilot services for integration into the main application.
"""

import os
import json
import logging
import re
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
import asyncio
import uuid

# Azure Document Intelligence
try:
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.core.credentials import AzureKeyCredential
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    print("Azure Document Intelligence not available. Install azure-ai-documentintelligence package.")

# Google Gemini
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Google Gemini not available. Install google-generativeai package.")

# PDF and image processing
try:
    import PyPDF2
    from PIL import Image
    import img2pdf
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("PDF processing not available. Install PyPDF2, Pillow, img2pdf, reportlab packages.")

# OpenCV for document visualization
try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    print("OpenCV not available. Install opencv-python package for document visualization.")

from models import db, DocumentAnalysis, WorkpaperBatch, BatchDocument, ClientDocument

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentAnalysisService:
    """Service for analyzing documents using Azure and Gemini AI"""
    
    def __init__(self):
        """Initialize the service with API credentials"""
        self.azure_endpoint = os.getenv('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT')
        self.azure_key = os.getenv('AZURE_DOCUMENT_INTELLIGENCE_KEY')
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        
        # Initialize Azure client
        if AZURE_AVAILABLE and self.azure_key and self.azure_endpoint:
            try:
                self.azure_client = DocumentIntelligenceClient(
                    endpoint=self.azure_endpoint,
                    credential=AzureKeyCredential(self.azure_key)
                )
                logger.info("Azure Document Intelligence client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Azure client: {e}")
                self.azure_client = None
        else:
            self.azure_client = None
            logger.warning("Azure Document Intelligence not configured")
        
        # Initialize Gemini
        if GEMINI_AVAILABLE and self.gemini_api_key:
            try:
                genai.configure(api_key=self.gemini_api_key)
                self.gemini_model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
                logger.info("Google Gemini client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                self.gemini_model = None
        else:
            self.gemini_model = None
            logger.warning("Google Gemini not configured")
        
        # PII patterns for basic handling
        self.pii_patterns = {
            'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b|\b\d{9}\b'),
            'ein': re.compile(r'\b\d{2}-\d{7}\b'),
            'phone': re.compile(r'\b\+?1?\s*\(?[2-9][0-8][0-9]\)?[-.\s]*[2-9][0-9]{2}[-.\s]*[0-9]{4}\b')
        }
    
    def analyze_document(self, client_document_id: int, firm_id: int) -> DocumentAnalysis:
        """
        Analyze a client document and store results in the database.
        
        Args:
            client_document_id: ID of the ClientDocument to analyze
            firm_id: ID of the firm
            
        Returns:
            DocumentAnalysis object with results
        """
        # Get the client document
        client_doc = ClientDocument.query.get(client_document_id)
        if not client_doc:
            raise ValueError(f"Client document {client_document_id} not found")
        
        # Check if analysis already exists
        existing_analysis = DocumentAnalysis.query.filter_by(
            client_document_id=client_document_id
        ).first()
        
        if existing_analysis:
            logger.info(f"Analysis already exists for document {client_document_id}")
            return existing_analysis
        
        # Create new analysis record
        analysis = DocumentAnalysis(
            client_document_id=client_document_id,
            firm_id=firm_id,
            processing_status='processing',
            processing_start_time=datetime.utcnow()
        )
        db.session.add(analysis)
        db.session.commit()
        
        try:
            # Read document file
            file_path = Path(client_doc.file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"Document file not found: {file_path}")
            
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Process with Azure if available
            if self.azure_client:
                azure_results = self._process_with_azure(file_content, client_doc.mime_type)
                analysis.azure_doc_type = azure_results.get('doc_type')
                analysis.azure_confidence = azure_results.get('confidence')
                analysis.azure_fields = azure_results.get('fields', {})
                analysis.azure_raw_response = azure_results.get('raw_response', {})
                analysis.azure_processing_time = azure_results.get('processing_time')
            
            # Process with Gemini if available
            if self.gemini_model:
                gemini_results = self._process_with_gemini(file_content, client_doc.original_filename)
                analysis.gemini_document_category = gemini_results.get('document_category')
                analysis.gemini_analysis_summary = gemini_results.get('analysis_summary')
                analysis.gemini_extracted_info = gemini_results.get('extracted_info', {})
                analysis.gemini_bookmark_structure = gemini_results.get('bookmark_structure', {})
                analysis.gemini_raw_response = gemini_results.get('raw_response', {})
                analysis.gemini_processing_time = gemini_results.get('processing_time')
            
            # Apply PII handling
            if analysis.azure_fields:
                analysis.azure_fields = self._apply_pii_handling(analysis.azure_fields)
                analysis.contains_pii = self._check_for_pii(analysis.azure_fields)
            
            # Validate results
            validation_errors = self._validate_analysis(analysis)
            analysis.validation_errors = validation_errors
            
            # Mark as completed
            analysis.processing_status = 'completed'
            analysis.processing_end_time = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Error analyzing document {client_document_id}: {e}")
            analysis.processing_status = 'error'
            analysis.processing_end_time = datetime.utcnow()
            analysis.validation_errors = [{'field': 'general', 'message': str(e), 'severity': 'error'}]
        
        db.session.commit()
        return analysis
    
    def _process_with_azure(self, file_content: bytes, mime_type: str) -> Dict[str, Any]:
        """Process document with Azure Document Intelligence"""
        start_time = datetime.utcnow()
        
        try:
            # Use prebuilt-tax model for tax documents
            poller = self.azure_client.begin_analyze_document(
                "prebuilt-tax.us", 
                file_content,
                content_type=mime_type
            )
            result = poller.result()
            
            # Extract fields
            fields = {}
            doc_type = "unknown"
            confidence = None
            
            if result.documents:
                first_doc = result.documents[0]
                doc_type = first_doc.doc_type if first_doc.doc_type else "unknown"
                confidence = first_doc.confidence if first_doc.confidence else None
                
                # Extract fields
                if first_doc.fields:
                    fields = self._extract_azure_fields(first_doc.fields)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                'doc_type': doc_type,
                'confidence': confidence,
                'fields': fields,
                'raw_response': result.to_dict(),
                'processing_time': processing_time
            }
            
        except Exception as e:
            logger.error(f"Azure processing error: {e}")
            return {
                'doc_type': 'error',
                'confidence': 0.0,
                'fields': {},
                'raw_response': {'error': str(e)},
                'processing_time': (datetime.utcnow() - start_time).total_seconds()
            }
    
    def _process_with_gemini(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Process document with Gemini AI"""
        start_time = datetime.utcnow()
        
        try:
            # Create prompt for tax document analysis
            prompt = """
            Analyze this tax document and provide:
            1. Document category (Income Documents, Deduction Documents, Tax Forms, etc.)
            2. Document type (W-2, 1099-MISC, Receipt, etc.)
            3. Key information extracted (amounts, names, dates, etc.)
            4. Brief analysis summary
            5. Suggested bookmark structure with 3 levels for workpaper organization
            
            Respond in JSON format with keys: document_category, document_type, extracted_info, analysis_summary, bookmark_structure
            """
            
            # Convert file to format Gemini can process
            if filename.lower().endswith('.pdf'):
                # For PDF, we'd need to convert to image first
                # For now, just analyze based on filename and basic structure
                response = self.gemini_model.generate_content([prompt, f"Document filename: {filename}"])
            else:
                # For images, we can send directly
                import io
                image = Image.open(io.BytesIO(file_content))
                response = self.gemini_model.generate_content([prompt, image])
            
            # Parse JSON response
            try:
                result_text = response.text
                # Clean up the response text
                result_text = result_text.strip()
                if result_text.startswith('```json'):
                    result_text = result_text[7:]
                if result_text.endswith('```'):
                    result_text = result_text[:-3]
                
                result_data = json.loads(result_text)
            except (json.JSONDecodeError, AttributeError):
                # Fallback if JSON parsing fails
                result_data = {
                    'document_category': 'Unknown',
                    'document_type': 'Unknown',
                    'extracted_info': {},
                    'analysis_summary': response.text if hasattr(response, 'text') else 'Analysis failed',
                    'bookmark_structure': {
                        'level1': 'Uncategorized Documents',
                        'level2': 'Unknown Type',
                        'level3': filename
                    }
                }
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                'document_category': result_data.get('document_category', 'Unknown'),
                'document_type': result_data.get('document_type', 'Unknown'),
                'extracted_info': result_data.get('extracted_info', {}),
                'analysis_summary': result_data.get('analysis_summary', ''),
                'bookmark_structure': result_data.get('bookmark_structure', {}),
                'raw_response': result_data,
                'processing_time': processing_time
            }
            
        except Exception as e:
            logger.error(f"Gemini processing error: {e}")
            return {
                'document_category': 'Error',
                'document_type': 'Error',
                'extracted_info': {},
                'analysis_summary': f"Analysis failed: {str(e)}",
                'bookmark_structure': {},
                'raw_response': {'error': str(e)},
                'processing_time': (datetime.utcnow() - start_time).total_seconds()
            }
    
    def _extract_azure_fields(self, azure_fields) -> Dict[str, Any]:
        """Extract and flatten fields from Azure response"""
        fields = {}
        
        for field_name, field_data in azure_fields.items():
            if hasattr(field_data, 'value') and field_data.value is not None:
                fields[field_name] = field_data.value
            elif hasattr(field_data, 'content') and field_data.content is not None:
                fields[field_name] = field_data.content
        
        return fields
    
    def _apply_pii_handling(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        """Apply PII masking to sensitive fields"""
        processed_fields = {}
        
        for field_name, field_value in fields.items():
            if isinstance(field_value, str):
                if self._is_pii_field(field_name, field_value):
                    processed_fields[field_name] = self._mask_pii_value(field_value)
                else:
                    processed_fields[field_name] = field_value
            else:
                processed_fields[field_name] = field_value
        
        return processed_fields
    
    def _is_pii_field(self, field_name: str, field_value: str) -> bool:
        """Check if field contains PII"""
        # Check field name patterns
        pii_field_patterns = [
            r'(?i)\b(?:ssn|tin|ein)\b',
            r'(?i)\b(?:social|security|tax(?:payer)?|employer)[\s_]*(?:number|id)\b'
        ]
        
        for pattern in pii_field_patterns:
            if re.search(pattern, field_name):
                return True
        
        # Check value patterns
        for pattern in self.pii_patterns.values():
            if pattern.search(field_value):
                return True
        
        return False
    
    def _mask_pii_value(self, value: str) -> str:
        """Mask PII in field value"""
        for pattern_name, pattern in self.pii_patterns.items():
            if pattern.search(value):
                if pattern_name == 'ssn':
                    if '-' in value and len(value) == 11:  # XXX-XX-XXXX
                        return f"XXX-XX-{value[-4:]}"
                    elif len(value) == 9:  # XXXXXXXXX
                        return f"XXXXX{value[-4:]}"
                elif pattern_name == 'ein':
                    if '-' in value and len(value) == 10:  # XX-XXXXXXX
                        return f"XX-XXX{value[-4:]}"
                elif pattern_name == 'phone':
                    return "XXX-XXX-XXXX"
        
        return "****"
    
    def _check_for_pii(self, fields: Dict[str, Any]) -> bool:
        """Check if any fields contain PII"""
        for field_name, field_value in fields.items():
            if isinstance(field_value, str):
                if self._is_pii_field(field_name, field_value):
                    return True
        return False
    
    def _validate_analysis(self, analysis: DocumentAnalysis) -> List[Dict[str, Any]]:
        """Validate analysis results"""
        errors = []
        
        # Check if we have any results
        if not analysis.has_azure_results and not analysis.has_gemini_results:
            errors.append({
                'field': 'general',
                'message': 'No analysis results obtained from either Azure or Gemini',
                'severity': 'error'
            })
        
        # Validate Azure results
        if analysis.azure_confidence is not None and analysis.azure_confidence < 0.5:
            errors.append({
                'field': 'azure_confidence',
                'message': f'Low confidence score: {analysis.azure_confidence:.2f}',
                'severity': 'warning'
            })
        
        return errors


class WorkpaperGenerationService:
    """Service for generating consolidated workpapers"""
    
    def __init__(self):
        """Initialize workpaper generation service"""
        self.output_folder = Path("temp/workpapers")
        self.output_folder.mkdir(parents=True, exist_ok=True)
    
    def generate_workpaper(self, client_id: int, firm_id: int, document_ids: List[int], 
                          batch_name: str, tax_year: str = None, preparer_name: str = None) -> WorkpaperBatch:
        """
        Generate a consolidated workpaper from client documents.
        
        Args:
            client_id: ID of the client
            firm_id: ID of the firm
            document_ids: List of ClientDocument IDs to include
            batch_name: Name for the workpaper batch
            tax_year: Tax year for the documents
            preparer_name: Name of the preparer
            
        Returns:
            WorkpaperBatch object with generated workpaper information
        """
        if not PDF_AVAILABLE:
            raise RuntimeError("PDF processing libraries not available")
        
        # Create batch record
        batch = WorkpaperBatch(
            firm_id=firm_id,
            client_id=client_id,
            batch_name=batch_name,
            tax_year=tax_year,
            preparer_name=preparer_name,
            status='processing',
            total_documents=len(document_ids)
        )
        db.session.add(batch)
        db.session.commit()
        
        try:
            # Get client documents and their analyses
            documents_with_analysis = []
            for doc_id in document_ids:
                client_doc = ClientDocument.query.get(doc_id)
                if client_doc:
                    analysis = DocumentAnalysis.query.filter_by(
                        client_document_id=doc_id
                    ).first()
                    documents_with_analysis.append((client_doc, analysis))
            
            if not documents_with_analysis:
                raise ValueError("No valid documents found")
            
            # Generate workpaper filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            workpaper_filename = f"workpaper_{batch.id}_{timestamp}.pdf"
            workpaper_path = self.output_folder / workpaper_filename
            
            # Create the PDF workpaper
            self._create_workpaper_pdf(documents_with_analysis, workpaper_path, batch)
            
            # Update batch with file information
            batch.workpaper_filename = workpaper_filename
            batch.workpaper_file_path = str(workpaper_path)
            batch.workpaper_file_size = workpaper_path.stat().st_size
            batch.status = 'completed'
            batch.completed_at = datetime.utcnow()
            batch.processed_documents = len(documents_with_analysis)
            
            # Create batch document records
            for i, (client_doc, analysis) in enumerate(documents_with_analysis):
                category = 'Uncategorized'
                doc_type = 'Unknown'
                
                if analysis and analysis.gemini_document_category:
                    category = analysis.gemini_document_category
                if analysis and analysis.gemini_bookmark_structure:
                    bookmark_data = analysis.gemini_bookmark_structure
                    if isinstance(bookmark_data, dict):
                        doc_type = bookmark_data.get('level2', 'Unknown')
                
                batch_doc = BatchDocument(
                    batch_id=batch.id,
                    client_document_id=client_doc.id,
                    document_analysis_id=analysis.id if analysis else None,
                    category=category,
                    document_type=doc_type,
                    sort_order=i
                )
                db.session.add(batch_doc)
            
            db.session.commit()
            logger.info(f"Workpaper generated successfully: {workpaper_path}")
            return batch
            
        except Exception as e:
            logger.error(f"Error generating workpaper: {e}")
            batch.status = 'error'
            db.session.commit()
            raise
    
    def _create_workpaper_pdf(self, documents_with_analysis: List, output_path: Path, batch: WorkpaperBatch):
        """Create the actual PDF workpaper"""
        from collections import defaultdict
        
        # Organize documents by category
        categorized_docs = defaultdict(list)
        for client_doc, analysis in documents_with_analysis:
            category = 'Uncategorized Documents'
            if analysis and analysis.gemini_document_category:
                category = analysis.gemini_document_category
            categorized_docs[category].append((client_doc, analysis))
        
        # Create PDF writer
        pdf_writer = PyPDF2.PdfWriter()
        
        # Add cover page
        cover_page = self._create_cover_page(batch, categorized_docs)
        pdf_writer.add_page(cover_page)
        
        # Track page numbers for bookmarks
        current_page = 1
        
        # Add documents by category
        for category, docs in categorized_docs.items():
            # Add category bookmark
            category_bookmark = pdf_writer.add_outline_item(category, current_page)
            
            for client_doc, analysis in docs:
                # Convert document to PDF if needed
                doc_pdf_path = self._ensure_pdf_format(client_doc)
                
                if doc_pdf_path and doc_pdf_path.exists():
                    with open(doc_pdf_path, 'rb') as f:
                        doc_reader = PyPDF2.PdfReader(f)
                        start_page = current_page
                        
                        for page in doc_reader.pages:
                            pdf_writer.add_page(page)
                            current_page += 1
                        
                        # Add document bookmark
                        doc_name = client_doc.original_filename
                        if analysis and analysis.gemini_bookmark_structure:
                            bookmark_data = analysis.gemini_bookmark_structure
                            if isinstance(bookmark_data, dict):
                                doc_name = bookmark_data.get('level3', doc_name)
                        
                        pdf_writer.add_outline_item(doc_name, start_page, parent=category_bookmark)
        
        # Write final PDF
        with open(output_path, 'wb') as output_file:
            pdf_writer.write(output_file)
        
        # Update page count
        batch.workpaper_page_count = current_page
    
    def _create_cover_page(self, batch: WorkpaperBatch, categorized_docs: Dict) -> Any:
        """Create a cover page for the workpaper"""
        import io
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=30
        )
        story.append(Paragraph(batch.batch_name, title_style))
        story.append(Spacer(1, 0.5*inch))
        
        # Information
        info_style = ParagraphStyle(
            'InfoStyle',
            parent=styles['Normal'],
            fontSize=12,
            leading=18
        )
        
        client_name = batch.client.name if batch.client else 'Unknown Client'
        info_data = [
            f"<b>Client:</b> {client_name}",
            f"<b>Generation Date:</b> {batch.created_at.strftime('%B %d, %Y')}",
            f"<b>Total Documents:</b> {batch.total_documents}"
        ]
        
        if batch.tax_year:
            info_data.insert(1, f"<b>Tax Year:</b> {batch.tax_year}")
        if batch.preparer_name:
            info_data.insert(-1, f"<b>Prepared By:</b> {batch.preparer_name}")
        
        for info in info_data:
            story.append(Paragraph(info, info_style))
            story.append(Spacer(1, 0.1*inch))
        
        story.append(Spacer(1, 0.5*inch))
        
        # Document summary
        story.append(Paragraph("Document Summary", styles['Heading2']))
        story.append(Spacer(1, 0.2*inch))
        
        table_data = [["Category", "Document Count"]]
        for category, docs in categorized_docs.items():
            table_data.append([category, str(len(docs))])
        
        table = Table(table_data, colWidths=[4*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(table)
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        # Read as PDF page
        reader = PyPDF2.PdfReader(buffer)
        return reader.pages[0]
    
    def _ensure_pdf_format(self, client_document: ClientDocument) -> Optional[Path]:
        """Ensure document is in PDF format, converting if necessary"""
        file_path = Path(client_document.file_path)
        if not file_path.exists():
            return None
        
        # If already PDF, return as is
        if client_document.mime_type == "application/pdf":
            return file_path
        
        # Convert image to PDF
        try:
            output_path = file_path.with_suffix('.pdf')
            
            # Don't reconvert if already exists
            if output_path.exists():
                return output_path
            
            # Convert using img2pdf for better quality
            with open(file_path, 'rb') as f:
                img_data = f.read()
            
            pdf_data = img2pdf.convert(img_data)
            
            with open(output_path, 'wb') as f:
                f.write(pdf_data)
            
            logger.info(f"Converted {file_path} to PDF: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error converting {file_path} to PDF: {e}")
            
            # Fallback: Try with PIL
            try:
                image = Image.open(file_path)
                output_path = file_path.with_suffix('.pdf')
                image.save(output_path, "PDF")
                return output_path
            except Exception as e2:
                logger.error(f"Fallback conversion also failed: {e2}")
                return None


class DocumentVisualizationService:
    """Service for creating document visualizations with field extraction overlays"""
    
    def __init__(self):
        """Initialize the document visualization service"""
        self.config = {
            'annotation_color': (0, 128, 255),  # Orange in BGR
            'annotation_thickness': 2,
            'box_alpha': 0.2,
            'font_scale': 0.5,
            'font_thickness': 1,
            'tick_size': 20,
            'tick_position_offset': 10,
            'visualization_type': 'both'  # 'box', 'tick', or 'both'
        }
    
    def create_annotated_image(self, document_analysis: DocumentAnalysis) -> Optional[str]:
        """
        Create an annotated image showing field extractions with tick marks and bounding boxes.
        
        Args:
            document_analysis: DocumentAnalysis object with Azure results
            
        Returns:
            Path to the annotated image file, or None if failed
        """
        if not OPENCV_AVAILABLE:
            logger.error("OpenCV not available for document visualization")
            return None
        
        if not document_analysis.azure_fields:
            logger.warning("No Azure field data available for visualization")
            return None
        
        # Get the original document
        client_doc = document_analysis.client_document
        if not client_doc or not client_doc.file_path:
            logger.error("No client document file path available")
            return None
        
        # Load the image
        try:
            image = cv2.imread(client_doc.file_path)
            if image is None:
                logger.error(f"Could not load image from {client_doc.file_path}")
                return None
            
            # Create annotations
            annotated_image = self._annotate_fields(image, document_analysis.azure_fields)
            
            # Save annotated image
            output_dir = Path("uploads") / f"client_{client_doc.client_id}" / "annotated"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            base_name = Path(client_doc.original_filename).stem
            output_path = output_dir / f"{base_name}_annotated.jpg"
            
            cv2.imwrite(str(output_path), annotated_image)
            logger.info(f"Created annotated image: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error creating annotated image: {e}")
            return None
    
    def _annotate_fields(self, image, azure_fields: Dict[str, Any]) -> Any:
        """
        Add field annotations to the image.
        
        Args:
            image: OpenCV image array
            azure_fields: Dictionary of Azure field extraction results
            
        Returns:
            Annotated image array
        """
        if not azure_fields:
            return image
        
        result_image = image.copy()
        
        # Process each field
        for field_name, field_data in azure_fields.items():
            if not isinstance(field_data, dict):
                continue
            
            # Look for bounding regions
            bounding_regions = field_data.get('boundingRegions', [])
            if not bounding_regions:
                continue
            
            for region in bounding_regions:
                if not isinstance(region, dict) or 'polygon' not in region:
                    continue
                
                polygon_coords = region.get('polygon', [])
                if len(polygon_coords) < 6:  # Need at least 3 points (6 coordinates)
                    continue
                
                # Draw annotations
                if self.config['visualization_type'] in ['box', 'both']:
                    result_image = self._draw_bounding_box(result_image, polygon_coords, field_name)
                
                if self.config['visualization_type'] in ['tick', 'both']:
                    result_image = self._draw_tick_mark(result_image, polygon_coords, field_name)
        
        return result_image
    
    def _draw_bounding_box(self, image, polygon_coords: List[float], label: str) -> Any:
        """Draw a bounding box around a field"""
        try:
            # Convert coordinates to numpy array
            points = np.array(
                [(int(polygon_coords[i]), int(polygon_coords[i+1])) 
                 for i in range(0, len(polygon_coords), 2)], 
                np.int32
            )
            points = points.reshape((-1, 1, 2))
            
            # Create overlay for transparency
            overlay = image.copy()
            color = self.config['annotation_color']
            
            # Draw filled polygon with transparency
            cv2.fillPoly(overlay, [points], color)
            cv2.addWeighted(overlay, self.config['box_alpha'], image, 1 - self.config['box_alpha'], 0, image)
            
            # Draw outline
            cv2.polylines(image, [points], True, color, self.config['annotation_thickness'])
            
            # Add label
            if label:
                # Find top-left corner for label placement
                min_x = min(p[0][0] for p in points)
                min_y = min(p[0][1] for p in points)
                
                # Clean up label (remove prefixes)
                clean_label = label.replace('_', ' ').title()
                if len(clean_label) > 15:
                    clean_label = clean_label[:12] + "..."
                
                # Draw label background
                text_size = cv2.getTextSize(
                    clean_label, cv2.FONT_HERSHEY_SIMPLEX, 
                    self.config['font_scale'], self.config['font_thickness']
                )[0]
                
                cv2.rectangle(
                    image, 
                    (min_x, min_y - text_size[1] - 8), 
                    (min_x + text_size[0] + 4, min_y), 
                    color, -1
                )
                
                # Draw label text
                cv2.putText(
                    image, clean_label, (min_x + 2, min_y - 4), 
                    cv2.FONT_HERSHEY_SIMPLEX, self.config['font_scale'], 
                    (255, 255, 255), self.config['font_thickness']
                )
            
            return image
            
        except Exception as e:
            logger.error(f"Error drawing bounding box for {label}: {e}")
            return image
    
    def _draw_tick_mark(self, image, polygon_coords: List[float], field_name: str) -> Any:
        """Draw a tick mark next to a field"""
        try:
            # Convert coordinates to bounding rectangle
            points = np.array(
                [(int(polygon_coords[i]), int(polygon_coords[i+1]))
                 for i in range(0, len(polygon_coords), 2)],
                np.int32
            ).reshape((-1, 1, 2))
            
            rect_x, rect_y, rect_w, rect_h = cv2.boundingRect(points)
            
            # Calculate tick mark position (to the right of the field)
            tick_x = rect_x + rect_w + self.config['tick_position_offset']
            tick_y = rect_y + rect_h // 2
            
            # Draw tick mark (checkmark)
            tick_size = self.config['tick_size']
            color = (0, 200, 0)  # Green color for tick
            thickness = self.config['annotation_thickness'] + 1
            
            # Checkmark points
            p1 = (tick_x, tick_y)
            p2 = (tick_x + tick_size // 3, tick_y + tick_size // 3)
            p3 = (tick_x + tick_size, tick_y - tick_size // 2)
            
            # Ensure points are within image bounds
            img_h, img_w = image.shape[:2]
            if all(0 <= x < img_w and 0 <= y < img_h for x, y in [p1, p2, p3]):
                cv2.line(image, p1, p2, color, thickness)
                cv2.line(image, p2, p3, color, thickness)
            
            return image
            
        except Exception as e:
            logger.error(f"Error drawing tick mark for {field_name}: {e}")
            return image