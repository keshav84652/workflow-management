"""
CPA Copilot - Streamlit Frontend
Main application interface for tax document processing.
"""

import streamlit as st
import asyncio
from pathlib import Path
import pandas as pd
import json
from datetime import datetime
import tempfile
import shutil
import os
import sys
import base64

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.services.document_processor import DocumentProcessor
from backend.services.workpaper_generator import WorkpaperGenerator
from backend.agents.tax_document_analyst_agent import TaxDocumentAnalystAgent
from backend.models.document import FileUpload, ProcessingBatch, ExportFormat
from backend.utils.config import settings

# Page configuration
st.set_page_config(
    page_title="CPA Copilot - Tax Document Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f4788;
        text-align: center;
        margin-bottom: 2rem;
    }
    .upload-section {
        background-color: #f0f2f6;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .processing-status {
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .success {
        background-color: #d4edda;
        color: #155724;
    }
    .error {
        background-color: #f8d7da;
        color: #721c24;
    }
    .warning {
        background-color: #fff3cd;
        color: #856404;
    }
    .chat-message {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 10px;
    }
    .user-message {
        background-color: #e3f2fd;
        color: #333333; /* Dark grey for readability */
        margin-left: 20%;
    }
    .agent-message {
        background-color: #f5f5f5;
        color: #333333; /* Dark grey for readability */
        margin-right: 20%;
    }
    .suggestion-button {
        margin: 0.2rem;
        padding: 0.3rem 0.8rem;
        background-color: #f0f2f6;
        border: 1px solid #ddd;
        border-radius: 15px;
        cursor: pointer;
        display: inline-block;
    }
    .suggestion-button:hover {
        background-color: #e0e2e6;
    }

    /* Adjust text input for better alignment and visual integration with button */
    div[data-testid="stTextInput"] > div:first-child {
        height: 40px; /* Match button height */
        display: flex;
        align-items: center;
    }
    div[data-testid="stTextInput"] > div > input {
        height: 100%; /* Make input fill its container */
        padding-top: 0.5rem; /* Adjust padding as needed */
        padding-bottom: 0.5rem;
        border-top-right-radius: 0 !important;
        border-bottom-right-radius: 0 !important;
        margin-right: -1px; /* Overlap borders */
    }

    /* Custom CSS for the send button */
    button[data-testid="stFormSubmitButton"] {
        border-radius: 50% !important; /* Make it round */
        width: 40px !important; /* Adjust size */
        height: 40px !important; /* Adjust size */
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 0 !important; /* Remove default padding */
        margin-left: -1px; /* Overlap borders */
        border-top-left-radius: 0 !important;
        border-bottom-left-radius: 0 !important;
        background-color: #1f4788; /* Example color */
        color: white;
    }
    button[data-testid="stFormSubmitButton"] > div { /* Target the inner div for icon alignment */
        display: flex;
        align-items: center;
        justify-content: center;
    }
</style>
""", unsafe_allow_html=True)


class CPACopilotApp:
    """Main Streamlit application class."""
    
    def __init__(self):
        """Initialize the application."""
        self.processor = DocumentProcessor()
        self.workpaper_generator = WorkpaperGenerator()
        self._init_session_state()
    
    def _init_session_state(self):
        """Initialize session state variables."""
        if 'uploaded_files' not in st.session_state:
            st.session_state.uploaded_files = []
        if 'processing_batch' not in st.session_state:
            st.session_state.processing_batch = None
        if 'processed_documents' not in st.session_state:
            st.session_state.processed_documents = []
        if 'workpaper_path' not in st.session_state:
            st.session_state.workpaper_path = None
        # Initialize processing configuration defaults
        if 'enable_azure' not in st.session_state:
            st.session_state.enable_azure = True
        if 'enable_gemini' not in st.session_state:
            st.session_state.enable_gemini = True
        if 'pii_mode' not in st.session_state:
            st.session_state.pii_mode = 'mask'
        # Initialize agent and chat
        if 'agent' not in st.session_state:
            st.session_state.agent = None
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        if 'show_suggestions' not in st.session_state:
            st.session_state.show_suggestions = False
        if 'current_suggestions' not in st.session_state:
            st.session_state.current_suggestions = []
    
    def run(self):
        """Run the main application."""
        # Header
        st.markdown('<h1 class="main-header">🏢 CPA Copilot</h1>', unsafe_allow_html=True)
        st.markdown('<p style="text-align: center; font-size: 1.2rem;">Your AI-Powered Tax Document Assistant</p>', unsafe_allow_html=True)
        
        # Sidebar configuration
        self._render_sidebar()
        
        # Main content
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📤 Upload Documents", "🔄 Process Documents", "📊 Results", "📄 Generate Workpaper", "🤖 AI Assistant", "🔍 Debug"])
        
        with tab1:
            self._render_upload_tab()
        
        with tab2:
            self._render_process_tab()
        
        with tab3:
            self._render_results_tab()
        
        with tab4:
            self._render_workpaper_tab()
        
        with tab5:
            self._render_agent_tab()
        
        with tab6:
            self._render_debug_tab()
    
    def _render_sidebar(self):
        """Render simplified sidebar."""
        st.sidebar.header("📊 CPA Copilot")
        
        # About
        st.sidebar.info(
            "**CPA Copilot** v1.0.0\n\n"
            "AI-powered tax document processing assistant that combines "
            "Azure Document Intelligence and Google Gemini AI for comprehensive "
            "document analysis and workpaper generation."
        )
    
    def _render_upload_tab(self):
        """Render document upload interface."""
        st.header("📤 Upload Tax Documents")
        st.markdown("Upload your tax documents for processing. Supported formats: PDF, JPG, PNG, TIFF")
        
        # File uploader
        uploaded_files = st.file_uploader(
            "Choose files",
            type=['pdf', 'jpg', 'jpeg', 'png', 'tiff'],
            accept_multiple_files=True,
            key="file_uploader"
        )
        
        if uploaded_files:
            # Process uploaded files
            new_files = []
            for uploaded_file in uploaded_files:
                # Check if already processed
                if not any(f.filename == uploaded_file.name for f in st.session_state.uploaded_files):
                    # Save to temp directory
                    temp_path = Path(settings.upload_folder) / uploaded_file.name
                    with open(temp_path, 'wb') as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Create FileUpload object
                    file_upload = FileUpload(
                        filename=uploaded_file.name,
                        content_type=uploaded_file.type,
                        size=uploaded_file.size,
                        file_path=temp_path
                    )
                    new_files.append(file_upload)
            
            if new_files:
                st.session_state.uploaded_files.extend(new_files)
                st.success(f"✅ Uploaded {len(new_files)} new file(s)")
        
        # Display uploaded files
        if st.session_state.uploaded_files:
            st.subheader("📁 Uploaded Files")
            
            # Create a dataframe for display
            file_data = []
            for f in st.session_state.uploaded_files:
                file_data.append({
                    "Filename": f.filename,
                    "Type": f.content_type.split('/')[-1].upper(),
                    "Size": f"{f.size / 1024:.1f} KB",
                    "Uploaded": f.upload_timestamp.strftime("%H:%M:%S")
                })
            
            df = pd.DataFrame(file_data)
            st.dataframe(df, use_container_width=True)
            
            # Clear files button
            col1, col2 = st.columns([1, 5])
            with col1:
                if st.button("🗑️ Clear All", type="secondary"):
                    # Clean up temp files
                    for f in st.session_state.uploaded_files:
                        if f.file_path and Path(f.file_path).exists():
                            Path(f.file_path).unlink()
                    st.session_state.uploaded_files = []
                    # Reset processing state
                    st.session_state.processed_documents = []
                    st.session_state.processing_batch = None
                    st.session_state.agent = None
                    st.rerun()
        else:
            st.info("👆 Upload tax documents to get started")
    
    def _render_process_tab(self):
        """Render document processing interface."""
        st.header("🔄 Process Documents")
        
        if not st.session_state.uploaded_files:
            st.warning("⚠️ Please upload documents first")
            return
        
        st.markdown(f"Ready to process **{len(st.session_state.uploaded_files)}** document(s)")
        
        # Processing Configuration (moved from sidebar)
        st.subheader("⚙️ Processing Configuration")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.session_state.enable_azure = st.checkbox(
                "Enable Azure Document Intelligence",
                value=st.session_state.get('enable_azure', True),
                help="Extract structured data using Azure's prebuilt tax models"
            )
        
        with col2:
            st.session_state.enable_gemini = st.checkbox(
                "Enable Gemini AI Analysis",
                value=st.session_state.get('enable_gemini', True),
                help="Analyze documents with Gemini for categorization and insights"
            )
        
        with col3:
            st.session_state.pii_mode = st.selectbox(
                "PII Handling Mode",
                options=["ignore", "mask", "remove"],
                index=1,
                help="How to handle personally identifiable information"
            )
        
        st.markdown("---")
        
        # Processing options summary
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Azure", "Enabled" if st.session_state.enable_azure else "Disabled")
        with col2:
            st.metric("Gemini", "Enabled" if st.session_state.enable_gemini else "Disabled")
        with col3:
            st.metric("PII Mode", st.session_state.pii_mode.capitalize())
        
        # Process button
        if st.button("🚀 Start Processing", type="primary", use_container_width=True):
            with st.spinner("Processing documents..."):
                # Run async processing
                batch = asyncio.run(self._process_documents())
                st.session_state.processing_batch = batch
                st.session_state.processed_documents = batch.documents
                
                # Initialize agent with processed documents
                st.session_state.agent = TaxDocumentAnalystAgent(st.session_state.processed_documents)
                
                # Show summary
                st.success(f"✅ Processing complete! Processed {batch.processed_documents} documents successfully.")
                
                if batch.failed_documents > 0:
                    st.error(f"❌ {batch.failed_documents} document(s) failed processing")
                
                # Show processing time
                total_time = sum(
                    doc.get_processing_duration() or 0 
                    for doc in batch.documents
                )
                st.info(f"⏱️ Total processing time: {total_time:.1f} seconds")
    
    async def _process_documents(self):
        """Process uploaded documents."""
        return await self.processor.process_batch(
            st.session_state.uploaded_files,
            enable_gemini=st.session_state.enable_gemini,
            enable_azure=st.session_state.enable_azure,
            pii_mode=st.session_state.pii_mode
        )
    
    def _render_results_tab(self):
        """Render processing results."""
        st.header("📊 Processing Results")
        
        if not st.session_state.processed_documents:
            st.info("📝 Process documents to see results")
            return
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        total_docs = len(st.session_state.processed_documents)
        successful = sum(1 for d in st.session_state.processed_documents if d.processing_status.value == "completed")
        failed = sum(1 for d in st.session_state.processed_documents if d.processing_status.value == "error")
        warnings = sum(len(d.validation_errors) for d in st.session_state.processed_documents)
        
        with col1:
            st.metric("Total Documents", total_docs)
        with col2:
            st.metric("Successful", successful, delta=f"{successful/total_docs*100:.0f}%")
        with col3:
            st.metric("Failed", failed)
        with col4:
            st.metric("Warnings", warnings)
        
        # Export all documents at once
        if st.session_state.processed_documents:
            st.subheader("📥 Bulk Export")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                json_data, json_filename = self._get_all_documents_json_export_data()
                if json_data:
                    st.download_button(
                        "💾 Export All as JSON",
                        json_data,
                        json_filename,
                        "application/json",
                        key="bulk_json_download"
                    )
                else:
                    st.info("No JSON data to export")
            
            with col2:
                csv_data, csv_filename = self._get_all_documents_csv_export_data()
                if csv_data:
                    st.download_button(
                        "📊 Export All as CSV",
                        csv_data,
                        csv_filename,
                        "text/csv",
                        key="bulk_csv_download"
                    )
                else:
                    st.info("No CSV data to export")
            
            with col3:
                clean_json_data, clean_json_filename = self._get_all_documents_cleaned_json_export_data()
                if clean_json_data:
                    st.download_button(
                        "🧹 Export Cleaned JSON",
                        clean_json_data,
                        clean_json_filename,
                        "application/json",
                        key="bulk_clean_json_download"
                    )
                else:
                    st.info("No cleaned JSON data to export")
                    
        st.subheader("📄 Document Details")
        
        for i, doc in enumerate(st.session_state.processed_documents):
            with st.expander(f"{doc.file_upload.filename} - {doc.processing_status.value.upper()}", expanded=False):
                # Summary
                summary = self.processor.get_document_summary(doc)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Azure Analysis**")
                    if doc.azure_result:
                        st.write(f"Document Type: **{doc.azure_result.doc_type}**")
                        st.write(f"Confidence: **{doc.azure_result.confidence:.2%}**" if doc.azure_result.confidence else "Confidence: N/A")
                        
                        # Key fields
                        if summary['key_fields']:
                            st.write("Key Fields:")
                            for field, value in summary['key_fields'].items():
                                st.write(f"- {field}: {value}")
                    else:
                        st.write("Not processed")
                
                with col2:
                    st.markdown("**Gemini Analysis**")
                    if doc.gemini_result:
                        st.write(f"Category: **{doc.gemini_result.document_category}**")
                        st.write(f"Summary: {doc.gemini_result.document_analysis_summary[:200]}...")
                        st.write(f"Bookmark: {doc.gemini_result.suggested_bookmark_structure.to_path()}")
                    else:
                        st.write("Not processed")
                
                # Validation errors
                if doc.validation_errors:
                    st.warning(f"⚠️ {len(doc.validation_errors)} validation issue(s)")
                    for error in doc.validation_errors:
                        st.write(f"- {error.field}: {error.message}")
                
                # Visualization options
                st.markdown("**Document Visualization**")
                viz_col1, viz_col2 = st.columns(2)
                
                with viz_col1:
                    if st.button(f"📋 View with Boxes & Ticks", key=f"viz_box_{i}"):
                        self._create_and_show_visualization(doc, 'box', f"box_viz_{i}")
                
                with viz_col2:
                    if st.button(f"✅ View with Tick Marks Only", key=f"viz_tick_{i}"):
                        self._create_and_show_visualization(doc, 'tick', f"tick_viz_{i}")
                
                # Show visualization if it exists in session state
                viz_key = f"visualization_{i}"
                if viz_key in st.session_state and st.session_state[viz_key]:
                    viz_type = st.session_state.get(f"viz_type_{i}", "box")
                    st.subheader(f"📸 Document Visualization ({viz_type.title()})")
                    st.image(st.session_state[viz_key], use_column_width=True)
                    
                    # Add download button for visualization
                    try:
                        with open(st.session_state[viz_key], 'rb') as f:
                            viz_filename = f"{Path(doc.file_upload.filename).stem}_{viz_type}_visualization.png"
                            st.download_button(
                                f"💾 Download {viz_type.title()} Visualization",
                                f.read(),
                                viz_filename,
                                "image/png",
                                key=f"viz_download_{i}"
                            )
                    except Exception as e:
                        st.error(f"Error preparing visualization download: {str(e)}")
                
                # Export options
                st.markdown("**Export Options**")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    json_data, json_filename = self._get_document_json_export_data(doc)
                    if json_data:
                        st.download_button(
                            "💾 Export JSON",
                            json_data,
                            json_filename,
                            "application/json",
                            key=f"json_download_{i}"
                        )
                    else:
                        st.info("No JSON data for this document")
                
                with col2:
                    csv_data, csv_filename = self._get_document_csv_export_data(doc)
                    if csv_data:
                        st.download_button(
                            "📊 Export CSV",
                            csv_data,
                            csv_filename,
                            "text/csv",
                            key=f"csv_download_{i}"
                        )
                    else:
                        st.info("No CSV data for this document")
                
                with col3:
                    if doc.azure_result:
                        raw_json = json.dumps(doc.azure_result.raw_response, indent=2)
                        st.download_button(
                            "⬇️ Raw Azure JSON",
                            raw_json,
                            f"{doc.file_upload.filename}_azure_raw.json",
                            "application/json",
                            key=f"raw_{i}"
                        )
    
    def _create_and_show_visualization(self, doc, viz_type, session_key):
        """Create and display document visualization."""
        try:
            # Create visualization
            viz_path = self.processor.create_document_visualization(
                doc, 
                visualization_type=viz_type
            )
            
            if viz_path and Path(viz_path).exists():
                # Store in session state for display
                doc_index = session_key.split('_')[-1]
                st.session_state[f"visualization_{doc_index}"] = viz_path
                st.session_state[f"viz_type_{doc_index}"] = viz_type
                st.success(f"✅ {viz_type.title()} visualization created successfully!")
                st.rerun()
            else:
                st.error("❌ Failed to create visualization. Please ensure OpenCV is installed.")
                
        except Exception as e:
            st.error(f"❌ Error creating visualization: {str(e)}")
            st.info("💡 To enable visualizations, install OpenCV: `pip install opencv-python`")
    
    def _get_all_documents_json_export_data(self):
        """Generates and returns JSON data for all processed documents."""
        export_data = self.processor.create_flat_export(
            st.session_state.processed_documents,
            include_metadata=True
        )
        json_str = json.dumps(export_data, indent=2, default=str)
        filename = f"tax_documents_flat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        return json_str, filename

    def _get_all_documents_cleaned_json_export_data(self):
        """Generates and returns cleaned JSON data for all processed documents."""
        cleaned_docs = []
        for doc in st.session_state.processed_documents:
            if doc.azure_result:
                cleaned_response = self.processor.clean_azure_response(
                    doc.azure_result.raw_response,
                    remove_page_details=True,
                    remove_confidence=False,
                    remove_spans=True
                )
                cleaned_docs.append({
                    "filename": doc.file_upload.filename,
                    "cleaned_azure_response": cleaned_response
                })
        json_str = json.dumps({"documents": cleaned_docs}, indent=2, default=str)
        filename = f"tax_documents_cleaned_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        return json_str, filename

    def _get_all_documents_csv_export_data(self):
        """Generates and returns CSV data for all processed documents."""
        export_data = self.processor.create_flat_export(
            st.session_state.processed_documents,
            include_metadata=True
        )
        csv_rows = []
        for doc_data in export_data["documents"]:
            flat_row = {}
            for key, value in doc_data.items():
                if isinstance(value, (dict, list)):
                    flat_row[key] = json.dumps(value, default=str)
                else:
                    flat_row[key] = value
            csv_rows.append(flat_row)
        
        if csv_rows:
            df = pd.DataFrame(csv_rows)
            csv = df.to_csv(index=False)
            filename = f"tax_documents_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            return csv, filename
        return None, None  # No data

    def _get_document_json_export_data(self, doc):
        """Generates and returns JSON data for a single processed document."""
        export_data = self.processor.create_flat_export([doc], include_metadata=True)
        json_str = json.dumps(export_data, indent=2, default=str)
        filename = f"{doc.file_upload.filename}_flat.json"
        return json_str, filename

    def _get_document_csv_export_data(self, doc):
        """Generates and returns CSV data for a single processed document."""
        export_data = self.processor.create_flat_export([doc], include_metadata=True)
        if export_data["documents"]:
            doc_data = export_data["documents"][0]
            flat_row = {}
            for key, value in doc_data.items():
                if isinstance(value, (dict, list)):
                    flat_row[key] = json.dumps(value, default=str)
                else:
                    flat_row[key] = value
            df = pd.DataFrame([flat_row])
            csv = df.to_csv(index=False)
            filename = f"{doc.file_upload.filename}_flat.csv"
            return csv, filename
        return None, None  # No data
    
    def _render_workpaper_tab(self):
        """Render workpaper generation interface."""
        st.header("📄 Generate Workpaper")
        
        if not st.session_state.processing_batch:
            st.info("📝 Process documents first to generate a workpaper")
            return
        
        st.markdown("Configure and generate a consolidated PDF workpaper with bookmarks")
        
        # Workpaper configuration
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input("Workpaper Title", value="Tax Document Workpaper")
            client_name = st.text_input("Client Name", placeholder="John Doe")
        
        with col2:
            tax_year = st.text_input("Tax Year", value="2023")
            preparer_name = st.text_input("Preparer Name", placeholder="Your Name")
        
        # Generate button
        if st.button("📑 Generate Workpaper", type="primary", use_container_width=True):
            with st.spinner("Generating workpaper..."):
                try:
                    workpaper_path = self.workpaper_generator.generate_workpaper(
                        st.session_state.processing_batch,
                        title=title,
                        client_name=client_name or None,
                        tax_year=tax_year or None,
                        preparer_name=preparer_name or None
                    )
                    st.session_state.workpaper_path = workpaper_path
                    st.success("✅ Workpaper generated successfully!")
                    
                    # Display workpaper info
                    if st.session_state.processing_batch.workpaper_metadata:
                        meta = st.session_state.processing_batch.workpaper_metadata
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Pages", meta.page_count)
                        with col2:
                            st.metric("File Size", f"{meta.file_size_bytes / 1024 / 1024:.1f} MB")
                        with col3:
                            st.metric("Documents", meta.total_documents)
                        
                        # Download button
                        with open(workpaper_path, 'rb') as f:
                            st.download_button(
                                "⬇️ Download Workpaper PDF",
                                f.read(),
                                file_name=workpaper_path.name,
                                mime="application/pdf",
                                use_container_width=True
                            )
                        
                        # Category breakdown
                        st.subheader("📊 Document Categories")
                        cat_df = pd.DataFrame(
                            meta.document_categories.items(),
                            columns=["Category", "Count"]
                        )
                        st.dataframe(cat_df, use_container_width=True)
                        
                except Exception as e:
                    st.error(f"❌ Error generating workpaper: {str(e)}")

    def _render_agent_tab(self):
        """Render AI assistant interface."""
        st.header("🤖 AI Tax Document Assistant")
        
        if not st.session_state.agent:
            if st.session_state.processed_documents:
                # Initialize agent with existing documents
                st.session_state.agent = TaxDocumentAnalystAgent(st.session_state.processed_documents)
                st.info("✅ Agent initialized with your processed documents!")
            else:
                st.warning("⚠️ Please upload and process documents first to enable the AI assistant.")
                return
        
        # Chat interface
        st.subheader("💬 Chat with AI Assistant")
        
        # Chat history display
        chat_container = st.container()
        
        with chat_container:
            for i, message in enumerate(st.session_state.chat_history):
                if message['role'] == 'user':
                    st.markdown(f"""
                    <div class="chat-message user-message">
                        <strong>You:</strong> {message['content']}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="chat-message agent-message">
                        <strong>Assistant:</strong> {message['content']}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Show tool results if available
                    if 'tool_results' in message and message['tool_results']:
                        with st.expander("🔧 Tool Results (Click to view raw data)", expanded=False):
                            for j, tool_result in enumerate(message['tool_results']):
                                st.json({
                                    f"Tool {j+1}": {
                                        "status": tool_result.status.value,
                                        "data": tool_result.data,
                                        "error": tool_result.error
                                    }
                                })
        
        # Suggested actions (only show if we have current suggestions and should show them)
        if st.session_state.show_suggestions and st.session_state.current_suggestions:
            st.markdown("**💡 Suggested Questions:**")
            suggestion_cols = st.columns(min(len(st.session_state.current_suggestions), 4))
            
            for i, suggestion in enumerate(st.session_state.current_suggestions):
                col_idx = i % len(suggestion_cols)
                with suggestion_cols[col_idx]:
                    if st.button(suggestion, key=f"suggestion_{i}", use_container_width=True):
                        # Clear suggestions when one is clicked
                        st.session_state.show_suggestions = False
                        st.session_state.current_suggestions = []
                        # Process the suggestion as a user message
                        asyncio.run(self._process_agent_message(suggestion))
                        st.rerun()
        
        # Chat input and send button within a form for Enter key submission
        with st.form(key="chat_form", clear_on_submit=True):
            col1, col2 = st.columns([7, 1])
            
            with col1:
                user_message = st.text_input(
                    "Ask me about your tax documents...",
                    placeholder="What is my total income?",
                    key="user_input_form_field", # Changed key to avoid conflict
                    label_visibility="collapsed" # Hide label for cleaner UI
                )
            
            with col2:
                send_button = st.form_submit_button("➤", type="primary", use_container_width=True) # Changed text to icon
            
            # Process message
            if send_button and user_message:
                # Clear suggestions when new message is sent
                st.session_state.show_suggestions = False
                st.session_state.current_suggestions = []
                
                asyncio.run(self._process_agent_message(user_message))
                st.rerun()
        
        # Download chat functionality
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 Download Chat History"):
                chat_data = self._export_chat_history()
                st.download_button(
                    "📥 Download JSON",
                    chat_data['json'],
                    chat_data['filename'],
                    "application/json"
                )
        
        with col2:
            if st.button("🗑️ Clear Chat"):
                st.session_state.chat_history = []
                st.session_state.show_suggestions = False
                st.session_state.current_suggestions = []
                if st.session_state.agent:
                    st.session_state.agent.conversation_memory.messages = []
                st.success("Chat cleared!")
                st.rerun()
        
        with col3:
            if st.button("🔄 Reset Agent"):
                if st.session_state.processed_documents:
                    st.session_state.agent = TaxDocumentAnalystAgent(st.session_state.processed_documents)
                    st.session_state.chat_history = []
                    st.session_state.show_suggestions = False
                    st.session_state.current_suggestions = []
                    st.success("Agent reset with current documents!")
                    st.rerun()
    
    async def _process_agent_message(self, message: str):
        """Process a message with the agent."""
        try:
            # Add user message to chat history
            st.session_state.chat_history.append({
                'role': 'user',
                'content': message,
                'timestamp': datetime.now().isoformat()
            })
            
            # Update agent with current documents (in case they changed)
            if st.session_state.processed_documents:
                st.session_state.agent.update_documents(st.session_state.processed_documents)
            
            # Process with agent
            response = await st.session_state.agent.process_message(message)
            
            # Add agent response to chat history
            agent_message = {
                'role': 'assistant',
                'content': response.message,
                'timestamp': datetime.now().isoformat()
            }
            
            # Include tool results if available
            if response.tool_results:
                agent_message['tool_results'] = response.tool_results
            
            st.session_state.chat_history.append(agent_message)
            
            # Update suggestions
            if response.suggested_actions:
                st.session_state.current_suggestions = response.suggested_actions
                st.session_state.show_suggestions = True
            
        except Exception as e:
            st.error(f"❌ Error processing message: {str(e)}")
            # Add error to chat history
            st.session_state.chat_history.append({
                'role': 'assistant',
                'content': f"I apologize, but I encountered an error: {str(e)}",
                'timestamp': datetime.now().isoformat()
            })
    
    def _export_chat_history(self):
        """Export chat history as JSON."""
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "total_messages": len(st.session_state.chat_history),
            "documents_processed": len(st.session_state.processed_documents) if st.session_state.processed_documents else 0,
            "chat_history": st.session_state.chat_history
        }
        
        json_str = json.dumps(export_data, indent=2, default=str)
        filename = f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        return {
            "json": json_str,
            "filename": filename
        }
    
    def _render_debug_tab(self):
        """Render debug information for API calls and tool executions."""
        from backend.utils.debug_logger import get_debug_data, get_api_calls_summary, get_tool_executions_summary, export_debug_session, clear_debug_data
        
        st.header("🔍 Debug Information")
        st.markdown("Monitor API calls, tool executions, and system performance in real-time.")
        
        # Debug controls
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Refresh Data", use_container_width=True):
                st.rerun()
        
        with col2:
            debug_data = get_debug_data()
            if st.download_button(
                "💾 Download Debug Session",
                export_debug_session(),
                f"debug_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "application/json",
                use_container_width=True
            ):
                st.success("Debug session exported!")
        
        with col3:
            if st.button("🗑️ Clear Debug Data", use_container_width=True):
                clear_debug_data()
                st.success("Debug data cleared!")
                st.rerun()
        
        # Summary metrics
        st.subheader("📊 Session Summary")
        
        debug_data = get_debug_data()
        api_summary = get_api_calls_summary()
        tool_summary = get_tool_executions_summary()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("API Calls", debug_data.get("total_api_calls", 0))
        with col2:
            st.metric("Tool Executions", debug_data.get("total_tool_executions", 0))
        with col3:
            if debug_data.get("total_api_calls", 0) > 0:
                st.metric("API Success Rate", f"{debug_data.get('api_success_rate', 0):.1f}%")
            else:
                st.metric("API Success Rate", "N/A")
        with col4:
            if debug_data.get("total_tool_executions", 0) > 0:
                st.metric("Tool Success Rate", f"{debug_data.get('tool_success_rate', 0):.1f}%")
            else:
                st.metric("Tool Success Rate", "N/A")
        
        # API Calls Section
        st.subheader("🌐 API Calls")
        
        if debug_data.get("total_api_calls", 0) == 0:
            st.info("No API calls recorded yet. Upload and process documents to see API activity.")
        else:
            # API Summary
            if "message" not in api_summary:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Total Calls", api_summary["total_calls"])
                    st.metric("Success Rate", f"{api_summary['success_rate']:.1f}%")
                
                with col2:
                    st.metric("Average Response Time", f"{api_summary['average_time_ms']:.1f}ms")
                    st.metric("Total Time", f"{api_summary['total_time_ms']:.1f}ms")
                
                # Service breakdown
                if api_summary.get("services"):
                    st.markdown("**Service Breakdown:**")
                    service_data = []
                    for service, stats in api_summary["services"].items():
                        success_rate = (stats["success"] / stats["count"]) * 100 if stats["count"] > 0 else 0
                        avg_time = stats["total_time"] / stats["count"] if stats["count"] > 0 else 0
                        service_data.append({
                            "Service": service.upper(),
                            "Calls": stats["count"],
                            "Success Rate": f"{success_rate:.1f}%",
                            "Avg Time (ms)": f"{avg_time:.1f}"
                        })
                    
                    if service_data:
                        df = pd.DataFrame(service_data)
                        st.dataframe(df, use_container_width=True)
            
            # Individual API calls
            st.markdown("**Recent API Calls:**")
            api_calls = debug_data.get("api_calls", [])
            
            for i, call in enumerate(reversed(api_calls[-10:])):  # Show last 10 calls
                timestamp = call.get("timestamp", "Unknown")
                service = call.get("service", "Unknown")
                endpoint = call.get("endpoint", "Unknown")
                status = call.get("status", "Unknown")
                response_time = call.get("response_time_ms", 0)
                error = call.get("error")
                
                # Color code based on status
                if status == "success":
                    status_color = "🟢"
                elif status == "error":
                    status_color = "🔴"
                else:
                    status_color = "🟡"
                
                with st.expander(f"{status_color} {service.upper()} - {endpoint} ({response_time:.1f}ms)", expanded=False):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Timestamp:** {timestamp}")
                        st.write(f"**Service:** {service}")
                        st.write(f"**Endpoint:** {endpoint}")
                        st.write(f"**Status:** {status}")
                        st.write(f"**Response Time:** {response_time:.1f}ms")
                        if error:
                            st.error(f"**Error:** {error}")
                    
                    with col2:
                        st.write("**Request Data:**")
                        st.json(call.get("request_data", {}))
                        
                        st.write("**Response Data:**")
                        st.json(call.get("response_data", {}))
        
        # Tool Executions Section
        st.subheader("🔧 Tool Executions")
        
        if debug_data.get("total_tool_executions", 0) == 0:
            st.info("No tool executions recorded yet. Use the AI Assistant to see tool activity.")
        else:
            # Tool Summary
            if "message" not in tool_summary:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Total Executions", tool_summary["total_executions"])
                    st.metric("Success Rate", f"{tool_summary['success_rate']:.1f}%")
                
                with col2:
                    st.metric("Average Execution Time", f"{tool_summary['average_time_ms']:.1f}ms")
                    st.metric("Total Time", f"{tool_summary['total_time_ms']:.1f}ms")
                
                # Tool breakdown
                if tool_summary.get("tools"):
                    st.markdown("**Tool Breakdown:**")
                    tool_data = []
                    for tool, stats in tool_summary["tools"].items():
                        success_rate = (stats["success"] / stats["count"]) * 100 if stats["count"] > 0 else 0
                        avg_time = stats["total_time"] / stats["count"] if stats["count"] > 0 else 0
                        tool_data.append({
                            "Tool": tool,
                            "Executions": stats["count"],
                            "Success Rate": f"{success_rate:.1f}%",
                            "Avg Time (ms)": f"{avg_time:.1f}"
                        })
                    
                    if tool_data:
                        df = pd.DataFrame(tool_data)
                        st.dataframe(df, use_container_width=True)
            
            # Individual tool executions
            st.markdown("**Recent Tool Executions:**")
            tool_executions = debug_data.get("tool_executions", [])
            
            for i, execution in enumerate(reversed(tool_executions[-10:])):  # Show last 10 executions
                timestamp = execution.get("timestamp", "Unknown")
                tool_name = execution.get("tool_name", "Unknown")
                status = execution.get("status", "Unknown")
                execution_time = execution.get("execution_time_ms", 0)
                error = execution.get("error")
                
                # Color code based on status
                if status == "success":
                    status_color = "🟢"
                elif status == "error":
                    status_color = "🔴"
                else:
                    status_color = "🟡"
                
                with st.expander(f"{status_color} {tool_name} ({execution_time:.1f}ms)", expanded=False):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Timestamp:** {timestamp}")
                        st.write(f"**Tool:** {tool_name}")
                        st.write(f"**Status:** {status}")
                        st.write(f"**Execution Time:** {execution_time:.1f}ms")
                        if error:
                            st.error(f"**Error:** {error}")
                    
                    with col2:
                        st.write("**Parameters:**")
                        st.json(execution.get("parameters", {}))
                        
                        st.write("**Result:**")
                        st.json(execution.get("result", {}))
        
        # Income Calculation Strategy
        st.subheader("💰 Income Calculation Strategy")
        
        st.markdown("""
        **The agent uses a sophisticated 3-tier approach for income calculation:**
        
        **Tier 1: Azure Document Intelligence (Primary)**
        - Uses Microsoft's prebuilt tax models
        - Maps specific fields: `WagesTipsAndOtherCompensation` (W-2), `OrdinaryDividends` (1099-DIV), etc.
        - High accuracy for standard tax forms
        
        **Tier 2: Gemini AI (Fallback)**
        - Uses Google's multimodal AI when Azure fails
        - Extracts from `extracted_key_info` fields like `box1`, `total_amount`
        - Handles non-standard or complex documents
        
        **Tier 3: Manual Parsing (Last Resort)**
        - Direct text extraction and parsing
        - Handles edge cases and corrupted data
        
        **Income Categories:**
        - **Wages**: W-2 employment income
        - **Dividends**: 1099-DIV investment income
        - **Interest**: 1099-INT bank/CD interest  
        - **Self Employment**: 1099-NEC contractor income
        - **Other**: 1099-MISC and miscellaneous income
        """)
        
        # Export options
        st.subheader("📥 Export Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Chat history export
            if st.session_state.chat_history:
                chat_data = self._export_chat_history()
                st.download_button(
                    "💬 Download Chat History",
                    chat_data['json'],
                    chat_data['filename'],
                    "application/json",
                    use_container_width=True
                )
            else:
                st.info("No chat history to export")
        
        with col2:
            # API data export
            if debug_data.get("total_api_calls", 0) > 0 or debug_data.get("total_tool_executions", 0) > 0:
                st.download_button(
                    "🔍 Download API & Tool Data",
                    export_debug_session(),
                    f"api_tool_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    "application/json",
                    use_container_width=True
                )
            else:
                st.info("No API/tool data to export")


def main():
    """Main entry point."""
    app = CPACopilotApp()
    app.run()


if __name__ == "__main__":
    main()
