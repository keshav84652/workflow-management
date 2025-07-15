"""
Workpaper Generator Service
Creates consolidated PDF workpapers with hierarchical bookmarks.
Adapted for workflow-management system.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
import io
from collections import defaultdict
import tempfile
import os

import PyPDF2
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from PIL import Image
import img2pdf

from core.db_import import db
from models import ClientDocument, ChecklistItem, DocumentChecklist, Client
from services.base import BaseService, transactional

# Set up logging
logger = logging.getLogger(__name__)


class WorkpaperMetadata:
    """Metadata for generated workpaper."""
    def __init__(self, title="Tax Document Workpaper", tax_year=None, preparer_name=None, 
                 client_name=None, total_documents=0):
        self.title = title
        self.tax_year = tax_year
        self.preparer_name = preparer_name
        self.client_name = client_name
        self.generation_date = datetime.now()
        self.total_documents = total_documents
        self.document_categories = {}
        self.output_path = None
        self.file_size_bytes = None
        self.page_count = None


class WorkpaperGeneratorService(BaseService):
    """Generates consolidated PDF workpapers with bookmarks."""
    
    def __init__(self):
        """Initialize workpaper generator."""
        super().__init__()
        self.output_folder = Path("temp/workpapers")
        self.output_folder.mkdir(parents=True, exist_ok=True)
        
    def generate_workpaper_from_checklist(
        self,
        checklist_id: int,
        firm_id: int,
        title: str = "Tax Document Workpaper",
        preparer_name: Optional[str] = None,
        client_name: Optional[str] = None,
        tax_year: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a consolidated PDF workpaper from a checklist's documents.
        
        Args:
            checklist_id: ID of the checklist
            firm_id: Firm ID for access control
            title: Title for the workpaper
            preparer_name: Name of the tax preparer
            client_name: Name of the client
            tax_year: Tax year for the documents
            
        Returns:
            Dict with success status and workpaper path
        """
        try:
            logger.info(f"Generating workpaper for checklist {checklist_id}")
            
            # Get checklist with access control
            checklist = DocumentChecklist.query.filter_by(
                id=checklist_id,
                firm_id=firm_id
            ).first()
            
            if not checklist:
                return {
                    'success': False,
                    'message': 'Checklist not found or access denied'
                }
            
            # Get all documents from the checklist
            documents = db.session.query(ClientDocument).join(
                ChecklistItem, ClientDocument.checklist_item_id == ChecklistItem.id
            ).filter(
                ChecklistItem.checklist_id == checklist_id,
                ClientDocument.file_path.isnot(None)
            ).all()
            
            if not documents:
                return {
                    'success': False,
                    'message': 'No documents found in checklist'
                }
            
            # Get client info if not provided
            if not client_name and checklist.client:
                client_name = checklist.client.name
            
            # Create metadata
            metadata = WorkpaperMetadata(
                title=title,
                tax_year=tax_year,
                preparer_name=preparer_name,
                client_name=client_name,
                total_documents=len(documents)
            )
            
            # Group documents by category
            categorized_docs = self._categorize_documents(documents)
            metadata.document_categories = {
                cat: len(docs) for cat, docs in categorized_docs.items()
            }
            
            # Generate output filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_client_name = "".join(c for c in (client_name or "client") if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_client_name = safe_client_name.replace(' ', '_')
            output_filename = f"workpaper_{safe_client_name}_{timestamp}.pdf"
            output_path = self.output_folder / output_filename
            
            # PRE-CALCULATE ACTUAL PAGE NUMBERS FOR TOC
            page_mapping = self._calculate_document_page_numbers(categorized_docs)
            
            # Create the PDF
            pdf_writer = PyPDF2.PdfWriter()
            
            # Add cover page
            cover_page = self._create_cover_page(metadata, categorized_docs)
            pdf_writer.add_page(cover_page)
            
            # Add table of contents with ACTUAL page numbers
            toc_pages = self._create_table_of_contents(categorized_docs, page_mapping)
            for page in toc_pages:
                pdf_writer.add_page(page)
            
            # Track page numbers for bookmarks
            current_page = 1 + len(toc_pages)  # Cover + TOC pages
            
            # Add documents by category with bookmarks
            for category, docs in categorized_docs.items():
                # Add category bookmark (Level 1)
                category_bookmark = pdf_writer.add_outline_item(
                    category, current_page
                )
                
                # Group by document type (Level 2)
                type_groups = defaultdict(list)
                for document in docs:
                    # Get document type from AI analysis or fallback to checklist item title
                    doc_type = self._get_document_type(document)
                    type_groups[doc_type].append(document)
                
                for doc_type, type_docs in type_groups.items():
                    # Add document type bookmark
                    type_bookmark = pdf_writer.add_outline_item(
                        doc_type, current_page, parent=category_bookmark
                    )
                    
                    # Add individual documents (Level 3)
                    for document in type_docs:
                        # Convert document to PDF if needed
                        doc_pdf_path = self._ensure_pdf_format(document)
                        
                        if doc_pdf_path and doc_pdf_path.exists():
                            # Add document pages
                            with open(doc_pdf_path, 'rb') as f:
                                doc_reader = PyPDF2.PdfReader(f)
                                start_page = current_page
                                
                                for page in doc_reader.pages:
                                    pdf_writer.add_page(page)
                                    current_page += 1
                                
                                # Add specific document bookmark
                                doc_name = self._get_document_name(document)
                                pdf_writer.add_outline_item(
                                    doc_name, start_page, parent=type_bookmark
                                )
            
            # Write final PDF
            with open(output_path, 'wb') as output_file:
                pdf_writer.write(output_file)
            
            # Update metadata
            metadata.output_path = output_path
            metadata.file_size_bytes = output_path.stat().st_size
            metadata.page_count = current_page
            
            logger.info(f"Workpaper generated successfully: {output_path}")
            
            return {
                'success': True,
                'message': 'Workpaper generated successfully',
                'workpaper_path': str(output_path),
                'metadata': {
                    'title': metadata.title,
                    'client_name': metadata.client_name,
                    'total_documents': metadata.total_documents,
                    'page_count': metadata.page_count,
                    'file_size_bytes': metadata.file_size_bytes
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating workpaper: {str(e)}")
            return {
                'success': False,
                'message': f'Error generating workpaper: {str(e)}'
            }
    
    def _calculate_document_page_numbers(
        self,
        categorized_docs: Dict[str, List[ClientDocument]]
    ) -> Dict[str, int]:
        """
        Pre-calculate actual page numbers for each document.
        
        Args:
            categorized_docs: Documents grouped by category
            
        Returns:
            Dictionary mapping document names to their starting page numbers
        """
        page_mapping = {}
        current_page = 3  # Start after cover page (1) and TOC (estimated 1-2 pages)
        
        # Estimate TOC pages first
        total_doc_count = sum(len(docs) for docs in categorized_docs.values())
        estimated_toc_pages = max(1, (total_doc_count // 20) + 1)
        current_page += estimated_toc_pages - 1
        
        try:
            for category, docs in categorized_docs.items():
                # Group by document type
                type_groups = defaultdict(list)
                for document in docs:
                    doc_type = self._get_document_type(document)
                    type_groups[doc_type].append(document)
                
                for doc_type, type_docs in type_groups.items():
                    for document in type_docs:
                        doc_name = self._get_document_name(document)
                        page_mapping[doc_name] = current_page
                        
                        # Calculate actual pages for this document
                        doc_pdf_path = self._ensure_pdf_format(document)
                        if doc_pdf_path and doc_pdf_path.exists():
                            try:
                                with open(doc_pdf_path, 'rb') as f:
                                    doc_reader = PyPDF2.PdfReader(f)
                                    doc_page_count = len(doc_reader.pages)
                                    current_page += doc_page_count
                            except Exception as e:
                                logger.warning(f"Could not count pages for {doc_pdf_path}: {str(e)}")
                                current_page += 1
                        else:
                            current_page += 1
            
            logger.info(f"Calculated page numbers for {len(page_mapping)} documents")
            return page_mapping
            
        except Exception as e:
            logger.error(f"Error calculating page numbers: {str(e)}")
            return {}
    
    def _categorize_documents(
        self,
        documents: List[ClientDocument]
    ) -> Dict[str, List[ClientDocument]]:
        """Categorize documents based on AI analysis or fallback rules."""
        categorized = defaultdict(list)
        
        for document in documents:
            category = "Tax Documents"  # Default category
            
            # Try to get category from AI analysis
            if document.ai_analysis:
                try:
                    analysis = document.ai_analysis
                    if isinstance(analysis, dict) and 'document_category' in analysis:
                        category = analysis['document_category']
                    elif isinstance(analysis, str):
                        # Simple keyword-based categorization
                        analysis_lower = analysis.lower()
                        if any(keyword in analysis_lower for keyword in ['income', 'w2', 'w-2', '1099']):
                            category = "Income Documents"
                        elif any(keyword in analysis_lower for keyword in ['deduction', '1098', 'receipt']):
                            category = "Deduction Documents"
                        elif any(keyword in analysis_lower for keyword in ['k1', 'k-1', 'schedule']):
                            category = "Partnership/S-Corp Documents"
                        else:
                            category = "Other Tax Documents"
                except Exception as e:
                    logger.warning(f"Error parsing AI analysis for document {document.id}: {str(e)}")
            
            # Fallback: categorize by checklist item title
            if category == "Tax Documents" and document.checklist_item:
                item_title = document.checklist_item.title.lower()
                if any(keyword in item_title for keyword in ['income', 'w2', 'w-2', '1099']):
                    category = "Income Documents"
                elif any(keyword in item_title for keyword in ['deduction', '1098', 'receipt']):
                    category = "Deduction Documents"
                elif any(keyword in item_title for keyword in ['k1', 'k-1', 'schedule']):
                    category = "Partnership/S-Corp Documents"
                else:
                    category = "Other Tax Documents"
            
            categorized[category].append(document)
        
        return dict(categorized)
    
    def _get_document_type(self, document: ClientDocument) -> str:
        """Get document type from AI analysis or fallback to checklist item."""
        if document.ai_analysis:
            try:
                analysis = document.ai_analysis
                if isinstance(analysis, dict) and 'document_type' in analysis:
                    return analysis['document_type']
                elif isinstance(analysis, str):
                    # Simple extraction
                    analysis_lower = analysis.lower()
                    if 'w-2' in analysis_lower or 'w2' in analysis_lower:
                        return "W-2"
                    elif '1099' in analysis_lower:
                        return "1099"
                    elif '1098' in analysis_lower:
                        return "1098"
                    elif 'k-1' in analysis_lower or 'k1' in analysis_lower:
                        return "Schedule K-1"
                    elif 'receipt' in analysis_lower:
                        return "Receipt"
            except Exception as e:
                logger.warning(f"Error parsing AI analysis for document type: {str(e)}")
        
        # Fallback to checklist item title
        if document.checklist_item:
            return document.checklist_item.title
        
        return "Document"
    
    def _get_document_name(self, document: ClientDocument) -> str:
        """Get document name for bookmarks."""
        if document.ai_analysis:
            try:
                analysis = document.ai_analysis
                if isinstance(analysis, dict) and 'document_name' in analysis:
                    return analysis['document_name']
            except Exception as e:
                logger.warning(f"Error parsing document name from AI analysis: {str(e)}")
        
        # Fallback to original filename
        return document.filename or f"Document {document.id}"
    
    def _create_cover_page(
        self,
        metadata: WorkpaperMetadata,
        categorized_docs: Dict[str, List[ClientDocument]]
    ) -> Any:
        """Create a cover page for the workpaper."""
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
        story.append(Paragraph(metadata.title, title_style))
        story.append(Spacer(1, 0.5*inch))
        
        # Document information
        info_style = ParagraphStyle(
            'InfoStyle',
            parent=styles['Normal'],
            fontSize=12,
            leading=18
        )
        
        info_data = []
        if metadata.client_name:
            info_data.append(f"<b>Client:</b> {metadata.client_name}")
        if metadata.tax_year:
            info_data.append(f"<b>Tax Year:</b> {metadata.tax_year}")
        if metadata.preparer_name:
            info_data.append(f"<b>Prepared By:</b> {metadata.preparer_name}")
        info_data.append(f"<b>Generation Date:</b> {metadata.generation_date.strftime('%B %d, %Y')}")
        info_data.append(f"<b>Total Documents:</b> {metadata.total_documents}")
        
        for info in info_data:
            story.append(Paragraph(info, info_style))
            story.append(Spacer(1, 0.1*inch))
        
        story.append(Spacer(1, 0.5*inch))
        
        # Document summary table
        story.append(Paragraph("Document Summary", styles['Heading2']))
        story.append(Spacer(1, 0.2*inch))
        
        # Create summary table
        table_data = [["Category", "Document Count"]]
        for category, count in metadata.document_categories.items():
            table_data.append([category, str(count)])
        
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
    
    def _create_table_of_contents(
        self,
        categorized_docs: Dict[str, List[ClientDocument]],
        page_mapping: Optional[Dict[str, int]] = None
    ) -> List[Any]:
        """Create table of contents pages with accurate page numbers."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # TOC Title
        story.append(Paragraph("Table of Contents", styles['Title']))
        story.append(Spacer(1, 0.5*inch))
        
        # TOC entries
        toc_style = ParagraphStyle(
            'TOCEntry',
            parent=styles['Normal'],
            fontSize=11,
            leftIndent=0
        )
        
        use_actual_pages = page_mapping is not None and len(page_mapping) > 0
        fallback_page_num = 3
        
        for category, docs in categorized_docs.items():
            # Category header
            story.append(Paragraph(f"<b>{category}</b>", toc_style))
            story.append(Spacer(1, 0.1*inch))
            
            # Group by type
            type_groups = defaultdict(list)
            for document in docs:
                doc_type = self._get_document_type(document)
                type_groups[doc_type].append(document)
            
            for doc_type, type_docs in type_groups.items():
                # Document type
                type_style = ParagraphStyle(
                    'TOCSubEntry',
                    parent=toc_style,
                    leftIndent=20
                )
                story.append(Paragraph(f"{doc_type}", type_style))
                
                # Individual documents
                doc_style = ParagraphStyle(
                    'TOCSubSubEntry',
                    parent=toc_style,
                    leftIndent=40,
                    fontSize=10
                )
                
                for document in type_docs:
                    doc_name = self._get_document_name(document)
                    
                    # Use actual page number if available
                    if use_actual_pages and doc_name in page_mapping:
                        page_num = page_mapping[doc_name]
                        story.append(Paragraph(f"{doc_name} ... Page {page_num}", doc_style))
                    else:
                        story.append(Paragraph(f"{doc_name} ... Page {fallback_page_num}", doc_style))
                        fallback_page_num += 2
                
                story.append(Spacer(1, 0.1*inch))
            
            story.append(Spacer(1, 0.2*inch))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        # Read pages
        reader = PyPDF2.PdfReader(buffer)
        return list(reader.pages)
    
    def _ensure_pdf_format(self, document: ClientDocument) -> Optional[Path]:
        """Ensure document is in PDF format, converting if necessary."""
        if not document.file_path:
            return None
            
        file_path = Path(document.file_path)
        if not file_path.exists():
            return None
        
        # If already PDF, return as is
        if document.file_path.lower().endswith('.pdf'):
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
            logger.error(f"Error converting {file_path} to PDF: {str(e)}")
            
            # Fallback: Try with PIL
            try:
                image = Image.open(file_path)
                output_path = file_path.with_suffix('.pdf')
                image.save(output_path, "PDF")
                return output_path
            except Exception as e2:
                logger.error(f"Fallback conversion also failed: {str(e2)}")
                return None