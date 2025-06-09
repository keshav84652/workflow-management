"""
Tax Document Analyst Agent
Main agent class that orchestrates tax document analysis using Gemini with function calling.
"""

import json
import logging
from typing import Dict, Any, List, Optional
import time

from google import genai
from google.genai import types

from .base_agent import BaseAgent, AgentResponse, ToolResultStatus
from .tax_document_tools import (
    DocumentInquiryTool,
    IncomeAggregatorTool,
    DocumentComparisonTool,
    ValidationReviewTool,
    MissingDataFinderTool
)
from .workflow_tools import (
    DocumentUploadTool,
    DocumentProcessingTool,
    WorkpaperGenerationTool
)
from ..models.document import ProcessedDocument
from ..utils.config import settings
from ..utils.debug_logger import log_tool_execution, log_api_call

logger = logging.getLogger(__name__)


class TaxDocumentAnalystAgent(BaseAgent):
    """Main agent for tax document analysis and assistance using Gemini."""
    
    def __init__(self, documents: Optional[List[ProcessedDocument]] = None):
        super().__init__(
            name="TaxDocumentAnalyst",
            description="AI assistant specialized in tax document analysis and processing"
        )
        
        # Initialize Gemini client
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model_name = settings.gemini_model
        
        # Initialize with documents
        self.documents = documents or []
        self._register_tools()
        
        # Gemini function declarations
        self.function_declarations = self._create_function_declarations()
        
        logger.info(f"Tax Document Analyst Agent initialized with {len(self.documents)} documents")
        
        # Log document details for debugging
        for i, doc in enumerate(self.documents):
            doc_type = "Unknown"
            if doc.azure_result:
                doc_type = doc.azure_result.doc_type
            elif doc.gemini_result:
                doc_type = doc.gemini_result.document_category
            logger.info(f"Document {i+1}: {doc.file_upload.filename} ({doc_type})")
    
    def update_documents(self, documents: List[ProcessedDocument]):
        """Update the documents available to the agent."""
        self.documents = documents
        # Re-register tools with updated documents
        self._register_tools()
        logger.info(f"Agent updated with {len(self.documents)} documents")
        
        # Log document details for debugging
        for i, doc in enumerate(self.documents):
            doc_type = "Unknown"
            field_count = 0
            
            if doc.azure_result:
                doc_type = doc.azure_result.doc_type
                field_count = len(doc.azure_result.fields) if doc.azure_result.fields else 0
            elif doc.gemini_result:
                doc_type = doc.gemini_result.document_category
                field_count = len(doc.gemini_result.extracted_key_info) if doc.gemini_result.extracted_key_info else 0
            
            logger.info(f"Document {i+1}: {doc.file_upload.filename} ({doc_type}) - {field_count} fields")
    
    def _register_tools(self):
        """Register all available tools with current documents."""
        # Clear existing tools
        self.tool_registry._tools.clear()
        
        # Register analysis tools with current documents
        self.register_tool(DocumentInquiryTool(self.documents))
        self.register_tool(IncomeAggregatorTool(self.documents))
        self.register_tool(DocumentComparisonTool(self.documents))
        self.register_tool(ValidationReviewTool(self.documents))
        self.register_tool(MissingDataFinderTool(self.documents))
        
        # Register workflow tools (these don't need documents)
        self.register_tool(DocumentUploadTool())
        self.register_tool(DocumentProcessingTool())
        self.register_tool(WorkpaperGenerationTool())
        
        logger.info(f"Registered {len(self.tool_registry.list_tools())} tools")
    
    def _create_function_declarations(self) -> List[types.FunctionDeclaration]:
        """Create Gemini function declarations from tools."""
        declarations = []
        
        # Document inquiry tool
        declarations.append(types.FunctionDeclaration(
            name="document_inquiry",
            description="Query specific document fields, search documents, or get complete document information",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "query_type": types.Schema(
                        type=types.Type.STRING,
                        enum=["field", "document", "search"],
                        description="Type of query to perform"
                    ),
                    "field_name": types.Schema(
                        type=types.Type.STRING,
                        description="Name of field to query (for field queries)"
                    ),
                    "document_name": types.Schema(
                        type=types.Type.STRING,
                        description="Name of document to retrieve (for document queries)"
                    ),
                    "search_value": types.Schema(
                        type=types.Type.STRING,
                        description="Value to search for (for search queries)"
                    ),
                },
                required=["query_type"]
            )
        ))
        
        # Income aggregator tool
        declarations.append(types.FunctionDeclaration(
            name="income_aggregator",
            description="Aggregate and calculate income data from tax documents",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "aggregation_type": types.Schema(
                        type=types.Type.STRING,
                        enum=["total", "detailed", "summary"],
                        description="Level of detail for aggregation"
                    ),
                    "income_type": types.Schema(
                        type=types.Type.STRING,
                        enum=["all", "wages", "dividends", "interest", "self_employment", "other"],
                        description="Type of income to aggregate"
                    )
                },
                required=[]
            )
        ))
        
        # Document comparison tool
        declarations.append(types.FunctionDeclaration(
            name="document_comparison",
            description="Compare data across documents or specific fields",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "comparison_type": types.Schema(
                        type=types.Type.STRING,
                        enum=["fields", "documents"],
                        description="Type of comparison"
                    ),
                    "field_names": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(type=types.Type.STRING),
                        description="Fields to compare (for field comparison)"
                    ),
                    "document_names": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(type=types.Type.STRING),
                        description="Documents to compare (for document comparison)"
                    )
                },
                required=["comparison_type"]
            )
        ))
        
        # Validation review tool
        declarations.append(types.FunctionDeclaration(
            name="validation_review",
            description="Review validation errors and data quality",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "review_type": types.Schema(
                        type=types.Type.STRING,
                        enum=["summary", "detailed"],
                        description="Level of detail for review"
                    )
                },
                required=[]
            )
        ))
        
        # Missing data finder tool
        declarations.append(types.FunctionDeclaration(
            name="missing_data_finder",
            description="Identify missing data and suggest required documents",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={},
                required=[]
            )
        ))
        
        # Workflow tools
        declarations.append(types.FunctionDeclaration(
            name="document_upload",
            description="Manage document uploads and file status",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "action": types.Schema(
                        type=types.Type.STRING,
                        enum=["status", "clear", "list"],
                        description="Upload management action to perform"
                    )
                },
                required=["action"]
            )
        ))
        
        declarations.append(types.FunctionDeclaration(
            name="document_processing",
            description="Process uploaded documents with AI analysis",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "action": types.Schema(
                        type=types.Type.STRING,
                        enum=["process", "status", "configure"],
                        description="Processing action to perform"
                    ),
                    "enable_azure": types.Schema(
                        type=types.Type.BOOLEAN,
                        description="Enable Azure Document Intelligence"
                    ),
                    "enable_gemini": types.Schema(
                        type=types.Type.BOOLEAN, 
                        description="Enable Gemini AI analysis"
                    ),
                    "pii_mode": types.Schema(
                        type=types.Type.STRING,
                        enum=["ignore", "mask", "remove"],
                        description="PII handling mode"
                    )
                },
                required=["action"]
            )
        ))
        
        declarations.append(types.FunctionDeclaration(
            name="workpaper_generation",
            description="Generate consolidated PDF workpapers",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "title": types.Schema(
                        type=types.Type.STRING,
                        description="Workpaper title"
                    ),
                    "client_name": types.Schema(
                        type=types.Type.STRING,
                        description="Client name"
                    ),
                    "tax_year": types.Schema(
                        type=types.Type.STRING,
                        description="Tax year"
                    ),
                    "preparer_name": types.Schema(
                        type=types.Type.STRING,
                        description="Preparer name"
                    )
                },
                required=[]
            )
        ))
        
        return declarations
    
    async def process_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Process a user message using Gemini with function calling."""
        try:
            # Add user message to memory
            self.add_to_memory("user", message)
            
            # If no documents available, provide helpful guidance
            if not self.documents:
                response_message = (
                    "I don't have any processed documents to analyze yet. "
                    "I can help you upload and process documents, or if you already have documents uploaded, "
                    "I can help you process them. Here's what I can do:\n\n"
                    "• **Document Management**: Upload, list, and organize tax documents\n"
                    "• **Document Processing**: Process documents with Azure and Gemini AI\n"
                    "• **Analysis**: Once documents are processed, I can analyze income, validate data, and find missing information\n"
                    "• **Workpaper Generation**: Create professional workpapers with bookmarks\n\n"
                    "Would you like to start by uploading some documents?"
                )
                
                self.add_to_memory("assistant", response_message)
                return AgentResponse(
                    message=response_message,
                    suggested_actions=[
                        "Check upload status",
                        "Process uploaded documents", 
                        "List uploaded files",
                        "Get processing configuration"
                    ]
                )
            
            # Prepare system prompt with detailed context
            system_prompt = self._create_detailed_system_prompt()
            
            # Create conversation messages
            messages = []
            
            # Add system message
            messages.append(
                types.Content(
                    role="user",
                    parts=[types.Part(text=system_prompt)]
                )
            )
            
            # Add conversation history (limit to last 10 messages)
            conversation_history = self.conversation_memory.get_context(include_system=False)
            for msg in conversation_history[-10:]:
                messages.append(
                    types.Content(
                        role="user" if msg["role"] == "user" else "model",
                        parts=[types.Part(text=msg["content"])]
                    )
                )
            
            # Add current message
            messages.append(
                types.Content(
                    role="user",
                    parts=[types.Part(text=f"User question: {message}")]
                )
            )
            
            logger.info(f"Processing message with {len(self.documents)} documents available")
            
            # Generate response with tools
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=messages,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(function_declarations=self.function_declarations)],
                    temperature=0.1,
                    top_p=0.95,
                    max_output_tokens=4096
                )
            )
            
            # Process the response
            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                
                # Check for function calls
                function_calls = []
                text_response = ""
                
                if candidate.content:
                    for part in candidate.content.parts:
                        if part.function_call:
                            function_calls.append(part.function_call)
                            logger.info(f"Function call detected: {part.function_call.name}")
                        elif part.text:
                            text_response += part.text
                
                # Execute function calls if present
                tool_results = []
                if function_calls:
                    for func_call in function_calls:
                        logger.info(f"Executing function: {func_call.name} with args: {dict(func_call.args)}")
                        tool_result = await self.execute_tool(func_call.name, dict(func_call.args))
                        tool_results.append(tool_result)
                        logger.info(f"Tool result status: {tool_result.status.value}")
                
                # Generate comprehensive response
                if tool_results or text_response:
                    final_response = await self._generate_comprehensive_response(
                        message, tool_results, text_response
                    )
                else:
                    final_response = "I understand your question. How can I help you with your tax documents?"
                
                # Add to memory
                self.add_to_memory("assistant", final_response)
                
                # Generate contextual suggested actions
                suggested_actions = self._generate_contextual_suggestions(tool_results, message)
                
                return AgentResponse(
                    message=final_response,
                    tool_results=tool_results if tool_results else None,
                    suggested_actions=suggested_actions,
                    confidence=0.95
                )
            
            else:
                error_message = "I didn't receive a proper response. Please try rephrasing your question."
                self.add_to_memory("assistant", error_message)
                return AgentResponse(message=error_message)
                
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            error_response = f"I apologize, but I encountered an error while processing your request. Please try again with a different question."
            self.add_to_memory("assistant", error_response)
            return AgentResponse(message=error_response)
    
    def _create_detailed_system_prompt(self) -> str:
        """Create a detailed system prompt with comprehensive document context."""
        # Build detailed document summary
        doc_details = []
        total_income_sources = []
        doc_types_present = set()
        
        for i, doc in enumerate(self.documents, 1):
            doc_info = f"Document {i}: {doc.file_upload.filename}"
            
            if doc.azure_result:
                doc_type = doc.azure_result.doc_type
                doc_types_present.add(doc_type)
                doc_info += f" (Type: {doc_type}"
                
                if doc.azure_result.confidence:
                    doc_info += f", Confidence: {doc.azure_result.confidence:.1%}"
                
                # Add key field information
                key_fields = []
                if doc.azure_result.fields:
                    # Look for important fields
                    for field, value in doc.azure_result.fields.items():
                        if any(key in field.lower() for key in ['wage', 'income', 'dividend', 'interest', 'compensation']):
                            if value and str(value).strip() and str(value) != "0":
                                key_fields.append(f"{field}: {value}")
                
                if key_fields:
                    doc_info += f", Key fields: {', '.join(key_fields[:3])}"  # Limit to 3 key fields
                
                doc_info += ")"
                
                # Track income sources
                if "w2" in doc_type.lower() or "w-2" in doc_type.lower():
                    total_income_sources.append("W-2 wages")
                elif "1099" in doc_type.lower():
                    total_income_sources.append(f"{doc_type} income")
            
            elif doc.gemini_result:
                doc_type = doc.gemini_result.document_category
                doc_info += f" (Category: {doc_type})"
                doc_types_present.add(doc_type)
            
            doc_details.append(doc_info)
        
        available_docs = "\n".join(doc_details)
        income_summary = f"Income sources available: {', '.join(set(total_income_sources))}" if total_income_sources else "No income sources identified yet"
        doc_types_summary = f"Document types: {', '.join(doc_types_present)}" if doc_types_present else "No document types identified"
        
        return f"""You are a Tax Document Analyst Agent, an expert AI assistant specializing in tax document analysis and processing.

CURRENT DOCUMENT PORTFOLIO:
{available_docs}

PORTFOLIO SUMMARY:
- Total documents: {len(self.documents)}
- {doc_types_summary}
- {income_summary}

YOUR CAPABILITIES:
You have access to specialized tools for comprehensive tax document analysis and workflow management:

**Analysis Tools:**
1. **document_inquiry**: Query specific fields, search for values, or get complete document details
2. **income_aggregator**: Calculate total income and provide detailed breakdowns by category
3. **document_comparison**: Compare data across documents to find discrepancies or patterns
4. **validation_review**: Check for errors, missing data, and data quality issues
5. **missing_data_finder**: Identify missing information and suggest additional documents needed

**Workflow Tools:**
6. **document_upload**: Manage document uploads and file status
7. **document_processing**: Process uploaded documents with AI analysis
8. **workpaper_generation**: Generate consolidated PDF workpapers

PROFESSIONAL GUIDELINES:
- Always be precise and accurate with financial data
- Use appropriate tools to gather information before responding
- Cite specific document sources when referencing data
- Highlight any uncertainties, discrepancies, or quality concerns
- Provide actionable insights and recommendations
- Maintain professional standards and client confidentiality

RESPONSE APPROACH:
1. Analyze the user's question to determine what information is needed
2. Use the most appropriate tool(s) to gather comprehensive data
3. Synthesize findings into a clear, professional response
4. Include specific data points, calculations, and source references
5. Provide relevant insights and next steps

Remember: You are working with real tax documents containing sensitive financial information. Always provide accurate, helpful analysis while maintaining the highest professional standards."""
    
    async def _generate_comprehensive_response(
        self,
        user_message: str,
        tool_results: List,
        text_response: str
    ) -> str:
        """Generate a comprehensive response integrating tool results with natural language."""
        
        if not tool_results:
            return text_response or "I've processed your request. How else can I help you?"
        
        # First, let's analyze the user's question and see if we can answer it using existing context + tool results
        intelligent_response = await self._analyze_user_intent_and_respond(user_message, tool_results)
        if intelligent_response:
            return intelligent_response
        
        # Fallback to structured tool result processing
        response_parts = []
        
        # Add any existing text response
        if text_response and text_response.strip():
            response_parts.append(text_response.strip())
        
        # Process each tool result
        for tool_result in tool_results:
            if tool_result.status == ToolResultStatus.SUCCESS:
                data = tool_result.data
                
                # Income aggregation results
                if "total_income" in data:
                    total = data.get("total_income", 0)
                    categories = data.get("income_by_category", {})
                    doc_count = data.get("document_count", 0)
                    
                    if total > 0:
                        response = f"📊 **Income Analysis**: I calculated your total income as **${total:,.2f}** from {doc_count} document(s)."
                        
                        if categories:
                            response += "\n\n**Breakdown by category:**"
                            for category, amount in categories.items():
                                percentage = (amount / total * 100) if total > 0 else 0
                                response += f"\n• {category.replace('_', ' ').title()}: ${amount:,.2f} ({percentage:.1f}%)"
                        
                        # Add document breakdown if available
                        if "document_breakdown" in data:
                            breakdown = data["document_breakdown"]
                            response += f"\n\n**Source documents:** {len(breakdown)} documents contributed to this total."
                    else:
                        response = "I didn't find any income amounts in your documents. This could mean the documents don't contain income information or there may be processing issues."
                    
                    response_parts.append(response)
                
                # Document inquiry results - Handle specific document data
                elif "filename" in data and ("azure_fields" in data or "gemini_extraction" in data):
                    filename = data.get("filename", "Document")
                    response = f"📄 **{filename} Details**:\n\n"
                    
                    # Check which data source has content
                    azure_fields = data.get("azure_fields", {})
                    gemini_extraction = data.get("gemini_extraction", {})
                    
                    # Use whichever has data (prefer Azure if both have data)
                    if azure_fields:
                        response += "**Extracted Information (Azure):**\n"
                        
                        # Organize fields by importance
                        key_fields = []
                        other_fields = []
                        
                        for field, value in azure_fields.items():
                            if field in ['TaxYear', 'Payer_Name', 'Recipient_Name', 'Employer_Name', 'Employee_Name']:
                                key_fields.append((field, value))
                            elif 'Box' in field or 'Amount' in field or 'Wage' in field or 'Income' in field:
                                key_fields.append((field, value))
                            else:
                                other_fields.append((field, value))
                        
                        # Display key fields first
                        for field, value in key_fields[:10]:  # Limit display
                            display_field = field.replace('_', ' ').title()
                            response += f"• **{display_field}**: {value}\n"
                        
                        if len(azure_fields) > 10:
                            response += f"• *...and {len(azure_fields) - 10} more fields*\n"
                    
                    elif gemini_extraction:
                        response += "**Extracted Information (Gemini AI):**\n"
                        
                        # Process Gemini extraction data
                        important_fields = [
                            ("form_type", "Form Type"),
                            ("tax_year", "Tax Year"),
                            ("payer_name", "Payer Name"),
                            ("payer_tin", "Payer TIN"),
                            ("recipient_name", "Recipient Name"),
                            ("recipient_tin", "Recipient TIN"),
                            ("box1", "Box 1 (Interest Income)"),
                            ("box2", "Box 2"),
                            ("box3", "Box 3"),
                            ("box4", "Box 4 (Federal Tax Withheld)"),
                            ("box5", "Box 5"),
                            ("box6", "Box 6"),
                            ("federal_tax_withheld", "Federal Tax Withheld"),
                            ("state_tax_withheld", "State Tax Withheld"),
                            ("total_amount", "Total Amount")
                        ]
                        
                        displayed_count = 0
                        for field_key, display_name in important_fields:
                            if field_key in gemini_extraction and gemini_extraction[field_key] != "Unknown":
                                value = gemini_extraction[field_key]
                                response += f"• **{display_name}**: {value}\n"
                                displayed_count += 1
                                if displayed_count >= 10:
                                    break
                        
                        # Count remaining fields
                        remaining = len([k for k, v in gemini_extraction.items() if v != "Unknown"]) - displayed_count
                        if remaining > 0:
                            response += f"• *...and {remaining} more fields*\n"
                    
                    else:
                        response += "**No extracted data available**\n"
                    
                    # Add document type and category
                    if "document_type" in data:
                        response += f"\n**Document Type**: {data['document_type']}"
                    if "category" in data:
                        response += f"\n**Category**: {data['category']}"
                    
                    response_parts.append(response)
                
                # Validation review results
                elif "total_documents" in data and "total_errors" in data:
                    total_docs = data.get("total_documents", 0)
                    total_errors = data.get("total_errors", 0)
                    docs_with_errors = data.get("documents_with_errors", 0)
                    error_breakdown = data.get("error_severity_breakdown", {})
                    
                    if total_errors == 0:
                        response = f"✅ **Validation Status**: Excellent! All {total_docs} documents passed validation without any errors."
                    else:
                        response = f"⚠️ **Validation Status**: I found {total_errors} validation issue(s) across {docs_with_errors} of your {total_docs} documents."
                        
                        if error_breakdown:
                            response += "\n\n**Issue breakdown:**"
                            for severity, count in error_breakdown.items():
                                response += f"\n• {severity.title()}: {count} issue(s)"
                        
                        response += "\n\n💡 *Recommendation: Review these issues to ensure data accuracy.*"
                    
                    response_parts.append(response)
                
                # Simple search results
                elif "results" in data:
                    results = data.get("results", [])
                    count = data.get("count", 0)
                    field_queried = tool_result.metadata.get("field_queried") if tool_result.metadata else "field"
                    
                    if count == 0:
                        response = f"🔍 **Search Results**: I didn't find any data for '{field_queried}' in your documents."
                    else:
                        response = f"🔍 **Search Results**: Found {count} result(s) for '{field_queried}':"
                        
                        for r in results[:5]:  # Limit to 5 results
                            doc_name = r.get('document', 'Unknown document')
                            value = r.get('value', 'N/A')
                            source = r.get('source', 'unknown')
                            response += f"\n• **{doc_name}**: {value} (via {source})"
                        
                        if count > 5:
                            response += f"\n• *...and {count - 5} more result(s)*"
                    
                    response_parts.append(response)
                
                # Missing data results
                elif "missing_fields" in data:
                    missing_fields = data.get("missing_fields", [])
                    suggested_docs = data.get("suggested_documents", [])
                    summary = data.get("summary", {})
                    
                    if not missing_fields and not suggested_docs:
                        response = "✅ **Data Completeness**: Your documents appear to be complete with all expected information present."
                    else:
                        response = "📋 **Missing Information Analysis**:"
                        
                        if missing_fields:
                            total_missing = summary.get("total_missing_fields", len(missing_fields))
                            response += f"\n\n**Missing fields**: {total_missing} field(s) are missing or empty across your documents."
                            
                            # Group by document
                            by_doc = {}
                            for field in missing_fields[:10]:  # Limit display
                                doc = field.get("document", "Unknown")
                                if doc not in by_doc:
                                    by_doc[doc] = []
                                by_doc[doc].append(field.get("field", "Unknown field"))
                            
                            for doc, fields in by_doc.items():
                                response += f"\n• **{doc}**: {', '.join(fields)}"
                        
                        if suggested_docs:
                            response += f"\n\n**Suggested additional documents**: {len(suggested_docs)} document type(s) might be needed:"
                            for suggestion in suggested_docs[:5]:  # Limit display
                                doc_type = suggestion.get("document_type", "Unknown")
                                reason = suggestion.get("reason", "No reason provided")
                                response += f"\n• **{doc_type}**: {reason}"
                    
                    response_parts.append(response)
                
                # Document comparison results
                elif "documents" in data and "common_fields" in data:
                    docs = data.get("documents", [])
                    common_fields = data.get("common_fields", [])
                    differences = data.get("differences", [])
                    
                    response = f"🔄 **Document Comparison**: Compared {len(docs)} documents."
                    response += f"\n\n**Common fields**: {len(common_fields)} field(s) found in all documents."
                    
                    if differences:
                        response += f"\n**Differences found**: {len(differences)} field(s) have different values:"
                        for diff in differences[:5]:  # Limit display
                            field = diff.get("field", "Unknown")
                            values = diff.get("values", {})
                            response += f"\n• **{field}**: {', '.join([f'{doc}={val}' for doc, val in values.items()])}"
                    else:
                        response += "\n✅ All common fields have consistent values across documents."
                    
                    response_parts.append(response)
                
                # Workflow tool results
                elif "message" in data:
                    response_parts.append(f"📋 **Workflow Update**: {data['message']}")
                
                # File listing results
                elif "uploaded_files" in data:
                    files = data.get("uploaded_files", [])
                    total_files = data.get("total_files", 0)
                    total_size = data.get("total_size_mb", 0)
                    
                    response = f"📁 **Available Documents**: I have access to {total_files} document(s) ({total_size:.1f} MB total):\n\n"
                    
                    for file_info in files:
                        filename = file_info.get("filename", "Unknown")
                        size_mb = file_info.get("size_mb", 0)
                        response += f"• **{filename}** ({size_mb:.1f} MB)\n"
                    
                    response_parts.append(response)
                
                # Generic data display
                else:
                    response_parts.append("I've gathered the requested information from your documents.")
            
            elif tool_result.status == ToolResultStatus.ERROR:
                response_parts.append(f"❌ I encountered an issue: {tool_result.error}")
        
        # Combine all response parts
        if response_parts:
            return "\n\n".join(response_parts)
        else:
            return "I've processed your request successfully."
    
    def _generate_contextual_suggestions(self, tool_results: List, user_message: str) -> List[str]:
        """Generate contextual suggested actions based on tool results and message."""
        if not self.documents:
            return [
                "Check upload status",
                "Process uploaded documents",
                "List uploaded files", 
                "Get processing configuration"
            ]
        
        suggestions = []
        
        # Analyze tool results for contextual suggestions
        if tool_results:
            for tool_result in tool_results:
                if tool_result.status == ToolResultStatus.SUCCESS:
                    data = tool_result.data
                    
                    # Income-related suggestions
                    if "total_income" in data:
                        suggestions.extend([
                            "Review validation errors",
                            "Find missing tax documents",
                            "Compare income across document types"
                        ])
                    
                    # Validation-related suggestions
                    elif "total_errors" in data:
                        if data.get("total_errors", 0) > 0:
                            suggestions.extend([
                                "Show detailed validation errors",
                                "Find missing information",
                                "Compare documents for discrepancies"
                            ])
                        else:
                            suggestions.extend([
                                "Calculate total income",
                                "Find missing information",
                                "Generate document summary"
                            ])
                    
                    # Missing data suggestions
                    elif "missing_fields" in data:
                        suggestions.extend([
                            "Calculate total income",
                            "Review document details",
                            "Check validation status"
                        ])
                    
                    # Workflow suggestions
                    elif "processing_complete" in data:
                        suggestions.extend([
                            "What is my total income?",
                            "Generate workpaper", 
                            "Review validation status"
                        ])
        
        # Add general suggestions based on available documents
        doc_types = set()
        for doc in self.documents:
            if doc.azure_result:
                doc_types.add(doc.azure_result.doc_type.lower())
        
        # Contextual suggestions based on document types
        if any("w2" in dt or "w-2" in dt for dt in doc_types):
            suggestions.append("Show W-2 wage details")
        
        if any("1099" in dt for dt in doc_types):
            suggestions.append("Analyze 1099 income types")
        
        # Base suggestions always available
        base_suggestions = [
            "What is my total income?",
            "Are there any validation errors?", 
            "What information is missing?",
            "Compare income across documents"
        ]
        
        # Combine and deduplicate
        all_suggestions = suggestions + base_suggestions
        unique_suggestions = []
        seen = set()
        
        for suggestion in all_suggestions:
            if suggestion not in seen:
                unique_suggestions.append(suggestion)
                seen.add(suggestion)
                if len(unique_suggestions) >= 4:
                    break
        
        return unique_suggestions
    
    async def _analyze_user_intent_and_respond(self, user_message: str, tool_results: List) -> Optional[str]:
        """
        Intelligently analyze user intent and provide contextual responses based on conversation history and tool results.
        This is the key method that makes the agent truly agentic.
        """
        user_msg_lower = user_message.lower()
        
        # Get recent conversation context
        recent_conversation = self.conversation_memory.get_context(include_system=False)[-6:]  # Last 6 messages
        
        # Look for specific intent patterns and context clues
        
        # 1. INTEREST/DIVIDEND AMOUNT QUESTIONS
        if any(term in user_msg_lower for term in ['int amount', 'interest amount', 'interest income', 'box 1', 'box1']):
            # Check if we have 1099-INT data in tool results or recent conversation
            for tool_result in tool_results:
                if tool_result.status == ToolResultStatus.SUCCESS:
                    data = tool_result.data
                    
                    # Check if this is 1099-INT document data
                    if "azure_fields" in data and any("1099" in str(data.get("filename", "")).upper() and "INT" in str(data.get("filename", "")).upper()):
                        azure_fields = data["azure_fields"]
                        
                        # Look for Box1 or interest income
                        interest_amount = None
                        box1_value = None
                        
                        # Check for transactions array (Azure format)
                        if "Transactions" in azure_fields and azure_fields["Transactions"]:
                            transaction = azure_fields["Transactions"][0]  # First transaction
                            if "Box1" in transaction:
                                box1_value = transaction["Box1"]
                                interest_amount = box1_value
                        
                        # Direct Box1 field
                        elif "Box1" in azure_fields:
                            box1_value = azure_fields["Box1"]
                            interest_amount = box1_value
                        
                        # Check Gemini extraction too
                        if not interest_amount and "gemini_extraction" in data:
                            gemini_data = data["gemini_extraction"]
                            if "box1" in gemini_data:
                                box1_text = gemini_data["box1"]
                                # Parse the amount from text like "123,456.00"
                                import re
                                amount_match = re.search(r'[\d,]+\.?\d*', box1_text.replace(',', ''))
                                if amount_match:
                                    try:
                                        interest_amount = float(amount_match.group().replace(',', ''))
                                        box1_value = interest_amount
                                    except:
                                        pass
                        
                        if interest_amount is not None:
                            payer_name = azure_fields.get("Payer_Name", "the payer")
                            tax_year = azure_fields.get("TaxYear", "2023")
                            
                            response = f"💰 **Interest Income**: Based on your 1099-INT from {payer_name}, your interest income (Box 1) for tax year {tax_year} is **${interest_amount:,.2f}**."
                            
                            # Add additional context if available
                            if "Transactions" in azure_fields and azure_fields["Transactions"]:
                                transaction = azure_fields["Transactions"][0]
                                if "Box4" in transaction and transaction["Box4"]:
                                    fed_tax = transaction["Box4"]
                                    response += f"\n\n📋 **Additional Info**: Federal income tax withheld (Box 4): ${fed_tax:,.2f}"
                            
                            response += f"\n\n💡 **Tax Note**: This interest income should be reported on your tax return as taxable income."
                            return response
            
            # Check conversation history for 1099-INT data
            for msg in recent_conversation:
                if msg.get("role") == "assistant" and "1099-INT" in msg.get("content", ""):
                    # Try to extract Box1 amount from previous conversation
                    content = msg["content"]
                    import re
                    # Look for Box1 patterns
                    box1_match = re.search(r'Box1[\'"]?\s*:\s*[\'"]?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', content)
                    if box1_match:
                        try:
                            amount = float(box1_match.group(1).replace(',', ''))
                            return f"💰 **Interest Income**: Based on your 1099-INT that I reviewed earlier, your interest income (Box 1) is **${amount:,.2f}**.\n\n💡 **Tax Note**: This interest income should be reported on your tax return as taxable income."
                        except:
                            pass
        
        # 2. WAGE/SALARY AMOUNT QUESTIONS
        elif any(term in user_msg_lower for term in ['wage', 'salary', 'w2', 'w-2', 'compensation']):
            for tool_result in tool_results:
                if tool_result.status == ToolResultStatus.SUCCESS:
                    data = tool_result.data
                    
                    if "azure_fields" in data and "W2" in str(data.get("filename", "")).upper():
                        azure_fields = data["azure_fields"]
                        
                        wages = azure_fields.get("WagesTipsAndOtherCompensation")
                        if wages:
                            employer = azure_fields.get("Employer_Name", "your employer")
                            tax_year = azure_fields.get("TaxYear", "2023")
                            
                            response = f"💼 **W-2 Wages**: Your wages, tips, and other compensation from {employer} for tax year {tax_year} is **${wages:,.2f}**."
                            
                            # Add federal withholding if available
                            fed_tax = azure_fields.get("FederalIncomeTaxWithheld")
                            if fed_tax:
                                response += f"\n\n📋 **Federal Tax Withheld**: ${fed_tax:,.2f}"
                            
                            return response
        
        # 3. DIVIDEND AMOUNT QUESTIONS
        elif any(term in user_msg_lower for term in ['dividend', 'div', '1099-div']):
            for tool_result in tool_results:
                if tool_result.status == ToolResultStatus.SUCCESS:
                    data = tool_result.data
                    
                    if "azure_fields" in data and "DIV" in str(data.get("filename", "")).upper():
                        azure_fields = data["azure_fields"]
                        
                        # Look for dividend fields
                        total_dividends = azure_fields.get("Box1a", azure_fields.get("TotalOrdinaryDividends"))
                        if total_dividends:
                            payer = azure_fields.get("Payer_Name", "the payer")
                            return f"📈 **Dividend Income**: Your total ordinary dividends from {payer} is **${total_dividends:,.2f}**."
        
        # 4. TOTAL INCOME QUESTIONS - Check if we already have income data
        elif any(term in user_msg_lower for term in ['total income', 'total', 'all income', 'combined income']):
            # Look for existing income data in tool results
            for tool_result in tool_results:
                if tool_result.status == ToolResultStatus.SUCCESS:
                    data = tool_result.data
                    
                    if "total_income" in data:
                        total = data.get("total_income", 0)
                        if total > 0:
                            categories = data.get("income_by_category", {})
                            doc_count = data.get("document_count", 0)
                            
                            response = f"💰 **Total Income Summary**: Your total income from all sources is **${total:,.2f}** based on {doc_count} document(s)."
                            
                            if categories:
                                response += "\n\n**Income Breakdown:**"
                                for category, amount in categories.items():
                                    percentage = (amount / total * 100) if total > 0 else 0
                                    response += f"\n• {category.replace('_', ' ').title()}: ${amount:,.2f} ({percentage:.1f}%)"
                            
                            return response
        
        # 5. DOCUMENT LISTING QUESTIONS
        elif any(term in user_msg_lower for term in ['what documents', 'which documents', 'what files', 'documents do you have']):
            for tool_result in tool_results:
                if tool_result.status == ToolResultStatus.SUCCESS:
                    data = tool_result.data
                    
                    if "uploaded_files" in data:
                        files = data.get("uploaded_files", [])
                        total_files = data.get("total_files", 0)
                        
                        if total_files > 0:
                            response = f"📁 **Document Portfolio**: I have access to {total_files} tax document(s):\n\n"
                            
                            # Categorize documents
                            tax_docs = []
                            for file_info in files:
                                filename = file_info.get("filename", "Unknown")
                                size_mb = file_info.get("size_mb", 0)
                                
                                # Identify document type
                                doc_type = "Document"
                                if "1099-INT" in filename.upper():
                                    doc_type = "1099-INT (Interest Income)"
                                elif "1099-DIV" in filename.upper():
                                    doc_type = "1099-DIV (Dividend Income)"
                                elif "1099-G" in filename.upper():
                                    doc_type = "1099-G (Government Payments)"
                                elif "1098-E" in filename.upper():
                                    doc_type = "1098-E (Student Loan Interest)"
                                elif "1098-T" in filename.upper():
                                    doc_type = "1098-T (Tuition Statement)"
                                elif "W2" in filename.upper() or "W-2" in filename.upper():
                                    doc_type = "W-2 (Wage Statement)"
                                elif "1040" in filename.upper():
                                    doc_type = "Form 1040 (Tax Return)"
                                
                                tax_docs.append((filename, doc_type, size_mb))
                            
                            # Display categorized documents
                            for filename, doc_type, size_mb in tax_docs:
                                response += f"• **{filename}** - {doc_type} ({size_mb:.1f} MB)\n"
                            
                            response += f"\n💡 **Ready to analyze**: I can help you analyze income, validate data, find missing information, or answer specific questions about any of these documents."
                            return response
        
        # 6. SPECIFIC DOCUMENT QUESTIONS
        elif any(doc_type in user_msg_lower for doc_type in ['1099-int', '1099int', '1099 int']):
            # User is asking about 1099-INT specifically
            for tool_result in tool_results:
                if tool_result.status == ToolResultStatus.SUCCESS:
                    data = tool_result.data
                    
                    if "azure_fields" in data and "1099-INT" in str(data.get("filename", "")).upper():
                        azure_fields = data["azure_fields"]
                        payer_name = azure_fields.get("Payer_Name", "Unknown Payer")
                        tax_year = azure_fields.get("TaxYear", "Unknown Year")
                        
                        # Extract key amounts
                        key_amounts = []
                        if "Transactions" in azure_fields and azure_fields["Transactions"]:
                            transaction = azure_fields["Transactions"][0]
                            
                            if "Box1" in transaction and transaction["Box1"]:
                                key_amounts.append(f"Box 1 (Interest Income): ${transaction['Box1']:,.2f}")
                            if "Box2" in transaction and transaction["Box2"]:
                                key_amounts.append(f"Box 2 (Early Withdrawal Penalty): ${transaction['Box2']:,.2f}")
                            if "Box4" in transaction and transaction["Box4"]:
                                key_amounts.append(f"Box 4 (Federal Tax Withheld): ${transaction['Box4']:,.2f}")
                        
                        response = f"📄 **1099-INT Summary**:\n\n"
                        response += f"**Payer**: {payer_name}\n"
                        response += f"**Tax Year**: {tax_year}\n\n"
                        
                        if key_amounts:
                            response += "**Key Amounts**:\n"
                            for amount in key_amounts:
                                response += f"• {amount}\n"
                        
                        return response
        
        # No specific pattern matched, return None to fall back to generic processing
        return None
