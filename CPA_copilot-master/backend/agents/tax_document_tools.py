"""
Tax Document Analysis Tools
Specific tools for analyzing tax documents in CPA Copilot.
"""

from typing import Dict, Any, List, Optional
import json
from collections import defaultdict

from .base_agent import BaseTool, ToolResult, ToolResultStatus, ToolSchema
from ..models.document import ProcessedDocument, ProcessingStatus


class DocumentInquiryTool(BaseTool):
    """Tool for querying specific document fields and data"""
    
    def __init__(self, documents: List[ProcessedDocument]):
        self.documents = documents
    
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """Query document data"""
        query_type = params.get("query_type", "field")
        
        if query_type == "field":
            return await self._query_field(params)
        elif query_type == "document":
            return await self._query_document(params)
        elif query_type == "search":
            return await self._search_documents(params)
        else:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                data=None,
                error=f"Unknown query type: {query_type}"
            )
    
    async def _query_field(self, params: Dict[str, Any]) -> ToolResult:
        """Query specific field across documents"""
        field_name = params.get("field_name")
        document_filter = params.get("document_filter")
        
        results = []
        for doc in self.documents:
            if document_filter and not self._matches_filter(doc, document_filter):
                continue
            
            # Search in Azure results
            if doc.azure_result and field_name in doc.azure_result.fields:
                results.append({
                    "document": doc.file_upload.filename,
                    "field": field_name,
                    "value": doc.azure_result.fields[field_name],
                    "source": "azure",
                    "confidence": doc.azure_result.confidence
                })
            
            # Search in Gemini results
            if doc.gemini_result and field_name in doc.gemini_result.extracted_key_info:
                results.append({
                    "document": doc.file_upload.filename,
                    "field": field_name,
                    "value": doc.gemini_result.extracted_key_info[field_name],
                    "source": "gemini"
                })
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            data={"results": results, "count": len(results)},
            metadata={"field_queried": field_name}
        )
    
    async def _query_document(self, params: Dict[str, Any]) -> ToolResult:
        """Get complete document information"""
        doc_name = params.get("document_name")
        
        for doc in self.documents:
            if doc.file_upload.filename == doc_name:
                data = {
                    "filename": doc.file_upload.filename,
                    "status": doc.processing_status.value,
                    "azure_fields": doc.azure_result.fields if doc.azure_result else {},
                    "gemini_extraction": doc.gemini_result.extracted_key_info if doc.gemini_result else {},
                    "document_type": doc.azure_result.doc_type if doc.azure_result else "Unknown",
                    "category": doc.gemini_result.document_category if doc.gemini_result else "Unknown",
                    "validation_errors": len(doc.validation_errors)
                }
                
                return ToolResult(
                    status=ToolResultStatus.SUCCESS,
                    data=data
                )
        
        return ToolResult(
            status=ToolResultStatus.ERROR,
            data=None,
            error=f"Document not found: {doc_name}"
        )
    
    async def _search_documents(self, params: Dict[str, Any]) -> ToolResult:
        """Search documents by value"""
        search_value = str(params.get("search_value", ""))
        
        matches = []
        for doc in self.documents:
            doc_matches = []
            
            # Search in Azure fields
            if doc.azure_result:
                for field, value in doc.azure_result.fields.items():
                    if search_value.lower() in str(value).lower():
                        doc_matches.append({
                            "field": field,
                            "value": value,
                            "source": "azure"
                        })
            
            # Search in Gemini fields
            if doc.gemini_result:
                for field, value in doc.gemini_result.extracted_key_info.items():
                    if search_value.lower() in str(value).lower():
                        doc_matches.append({
                            "field": field,
                            "value": value,
                            "source": "gemini"
                        })
            
            if doc_matches:
                matches.append({
                    "document": doc.file_upload.filename,
                    "matches": doc_matches
                })
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            data={"matches": matches, "total_matches": len(matches)}
        )
    
    def _matches_filter(self, doc: ProcessedDocument, filter_spec: Dict) -> bool:
        """Check if document matches filter criteria"""
        # Simple filter implementation
        if "document_type" in filter_spec:
            if doc.azure_result and doc.azure_result.doc_type != filter_spec["document_type"]:
                return False
        
        if "category" in filter_spec:
            if doc.gemini_result and doc.gemini_result.document_category != filter_spec["category"]:
                return False
        
        return True
    
    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="document_inquiry",
            description="Query and search document data",
            parameters={
                "type": "object",
                "properties": {
                    "query_type": {
                        "type": "string",
                        "enum": ["field", "document", "search"],
                        "description": "Type of query to perform"
                    },
                    "field_name": {
                        "type": "string",
                        "description": "Name of field to query (for field queries)"
                    },
                    "document_name": {
                        "type": "string",
                        "description": "Name of document to retrieve (for document queries)"
                    },
                    "search_value": {
                        "type": "string",
                        "description": "Value to search for (for search queries)"
                    },
                    "document_filter": {
                        "type": "object",
                        "description": "Optional filter criteria"
                    }
                },
                "required": ["query_type"]
            },
            returns={
                "type": "object",
                "description": "Query results"
            }
        )


class IncomeAggregatorTool(BaseTool):
    """Tool for aggregating income data across documents"""
    
    def __init__(self, documents: List[ProcessedDocument]):
        self.documents = documents
    
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """Aggregate income data"""
        aggregation_type = params.get("aggregation_type", "total")
        income_type = params.get("income_type", "all")
        
        income_data = defaultdict(float)
        document_breakdown = []
        
        for doc in self.documents:
            # Try Azure results first
            if doc.azure_result and doc.azure_result.doc_type and doc.azure_result.fields:
                doc_type = doc.azure_result.doc_type.upper()
                
                # W-2 Income
                if "W2" in doc_type or "W-2" in doc_type:
                    wages = self._extract_numeric_value(
                        doc.azure_result.fields.get("WagesTipsAndOtherCompensation", 0)
                    )
                    if wages > 0:
                        income_data["wages"] += wages
                        document_breakdown.append({
                            "document": doc.file_upload.filename,
                            "type": "W-2",
                            "category": "wages",
                            "amount": wages
                        })
                
                # 1099 Income - FIXED EXTRACTION LOGIC
                elif "1099" in doc_type:
                    # Try to extract from Azure transaction structure first
                    income_amount = self._extract_income_from_azure_transactions(
                        doc.azure_result.fields, doc_type
                    )
                    
                    if income_amount and income_amount > 0:
                        # Categorize based on 1099 type
                        if "DIV" in doc_type:
                            income_data["dividends"] += income_amount
                            document_breakdown.append({
                                "document": doc.file_upload.filename,
                                "type": "1099-DIV",
                                "category": "dividends",
                                "amount": income_amount
                            })
                        elif "INT" in doc_type:
                            income_data["interest"] += income_amount
                            document_breakdown.append({
                                "document": doc.file_upload.filename,
                                "type": "1099-INT",
                                "category": "interest",
                                "amount": income_amount
                            })
                        elif "NEC" in doc_type:
                            income_data["self_employment"] += income_amount
                            document_breakdown.append({
                                "document": doc.file_upload.filename,
                                "type": "1099-NEC",
                                "category": "self_employment",
                                "amount": income_amount
                            })
                        elif "G" in doc_type:
                            income_data["other"] += income_amount
                            document_breakdown.append({
                                "document": doc.file_upload.filename,
                                "type": "1099-G",
                                "category": "other",
                                "amount": income_amount
                            })
                        elif "MISC" in doc_type:
                            income_data["other"] += income_amount
                            document_breakdown.append({
                                "document": doc.file_upload.filename,
                                "type": "1099-MISC",
                                "category": "other",
                                "amount": income_amount
                            })
            
            # If no Azure results or no income found, try Gemini results
            elif doc.gemini_result and doc.gemini_result.extracted_key_info:
                gemini_data = doc.gemini_result.extracted_key_info
                form_type = gemini_data.get("form_type", "").upper()
                
                # Extract income based on form type
                if "W-2" in form_type or "W2" in form_type:
                    # Look for wage fields
                    wages = self._extract_numeric_value(gemini_data.get("box1", 0))
                    if wages > 0:
                        income_data["wages"] += wages
                        document_breakdown.append({
                            "document": doc.file_upload.filename,
                            "type": "W-2",
                            "category": "wages",
                            "amount": wages
                        })
                
                elif "1099" in form_type:
                    # Extract income based on 1099 type
                    if "INT" in form_type:
                        # Box 1 is interest income for 1099-INT
                        interest = self._extract_numeric_value(gemini_data.get("box1", 0))
                        if interest > 0:
                            income_data["interest"] += interest
                            document_breakdown.append({
                                "document": doc.file_upload.filename,
                                "type": "1099-INT",
                                "category": "interest",
                                "amount": interest
                            })
                    
                    elif "DIV" in form_type:
                        # Box 1a is ordinary dividends for 1099-DIV
                        dividends = self._extract_numeric_value(gemini_data.get("box1a", gemini_data.get("box1", 0)))
                        if dividends > 0:
                            income_data["dividends"] += dividends
                            document_breakdown.append({
                                "document": doc.file_upload.filename,
                                "type": "1099-DIV",
                                "category": "dividends",
                                "amount": dividends
                            })
                    
                    elif "G" in form_type and "1099-G" in form_type:
                        # Box 1 is unemployment compensation for 1099-G
                        govt_payments = self._extract_numeric_value(gemini_data.get("box1", 0))
                        if govt_payments > 0:
                            income_data["other"] += govt_payments
                            document_breakdown.append({
                                "document": doc.file_upload.filename,
                                "type": "1099-G",
                                "category": "other",
                                "amount": govt_payments
                            })
                    
                    # Generic 1099 handling - try total_amount or box1
                    elif gemini_data.get("total_amount") or gemini_data.get("box1"):
                        amount = self._extract_numeric_value(
                            gemini_data.get("total_amount", gemini_data.get("box1", 0))
                        )
                        if amount > 0:
                            income_data["other"] += amount
                            document_breakdown.append({
                                "document": doc.file_upload.filename,
                                "type": form_type if form_type else "1099",
                                "category": "other",
                                "amount": amount
                            })
        
        # Calculate totals
        total_income = sum(income_data.values())
        
        # Prepare response based on aggregation type
        if aggregation_type == "total":
            result_data = {
                "total_income": total_income,
                "income_by_category": dict(income_data),
                "document_count": len(document_breakdown)
            }
        elif aggregation_type == "detailed":
            result_data = {
                "total_income": total_income,
                "income_by_category": dict(income_data),
                "document_breakdown": document_breakdown
            }
        else:
            result_data = {
                "total_income": total_income,
                "categories": list(income_data.keys())
            }
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            data=result_data,
            metadata={"documents_processed": len(self.documents)}
        )
    
    def _extract_numeric_value(self, value: Any) -> float:
        """Extract numeric value from various formats"""
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            # Remove common formatting
            cleaned = value.replace("$", "").replace(",", "").strip()
            try:
                return float(cleaned)
            except ValueError:
                return 0.0
        
        return 0.0
    
    def _extract_income_from_azure_transactions(self, azure_fields: Dict[str, Any], doc_type: str) -> Optional[float]:
        """
        Extract income from Azure transaction data structure.
        
        The Azure Document Intelligence API returns 1099 data in a nested structure:
        {
            "Transactions": [
                {
                    "Box1": 123456,
                    "Box2": 54321,
                    ...
                }
            ]
        }
        """
        transactions = azure_fields.get("Transactions", [])
        if not transactions or not isinstance(transactions, list):
            return None
        
        transaction = transactions[0]  # Get first transaction
        
        if "INT" in doc_type.upper():
            # For 1099-INT: Box1 is interest income
            return self._extract_numeric_value(transaction.get("Box1", 0))
        
        elif "DIV" in doc_type.upper():
            # For 1099-DIV: Box1a is ordinary dividends, fallback to Box1
            return self._extract_numeric_value(
                transaction.get("Box1a", transaction.get("Box1", 0))
            )
        
        elif "G" in doc_type.upper():
            # For 1099-G: Box1 is unemployment compensation or state/local tax refunds
            return self._extract_numeric_value(transaction.get("Box1", 0))
        
        elif "NEC" in doc_type.upper():
            # For 1099-NEC: Box1 is nonemployee compensation
            return self._extract_numeric_value(transaction.get("Box1", 0))
        
        elif "MISC" in doc_type.upper():
            # For 1099-MISC: Can be in various boxes, try common ones
            for box in ["Box1", "Box3", "Box7"]:
                value = self._extract_numeric_value(transaction.get(box, 0))
                if value > 0:
                    return value
        
        return None
    
    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="income_aggregator",
            description="Aggregate income data from tax documents",
            parameters={
                "type": "object",
                "properties": {
                    "aggregation_type": {
                        "type": "string",
                        "enum": ["total", "detailed", "summary"],
                        "description": "Level of detail for aggregation"
                    },
                    "income_type": {
                        "type": "string",
                        "enum": ["all", "wages", "dividends", "interest", "self_employment", "other"],
                        "description": "Type of income to aggregate"
                    }
                },
                "required": []
            },
            returns={
                "type": "object",
                "description": "Aggregated income data"
            }
        )


class DocumentComparisonTool(BaseTool):
    """Tool for comparing data across documents"""
    
    def __init__(self, documents: List[ProcessedDocument]):
        self.documents = documents
    
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """Compare documents or fields"""
        comparison_type = params.get("comparison_type", "fields")
        
        if comparison_type == "fields":
            return await self._compare_fields(params)
        elif comparison_type == "documents":
            return await self._compare_documents(params)
        else:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                data=None,
                error=f"Unknown comparison type: {comparison_type}"
            )
    
    async def _compare_fields(self, params: Dict[str, Any]) -> ToolResult:
        """Compare specific fields across documents"""
        field_names = params.get("field_names", [])
        
        comparison_data = []
        
        for field_name in field_names:
            field_values = []
            
            for doc in self.documents:
                value = None
                source = None
                
                # Check Azure results
                if doc.azure_result and field_name in doc.azure_result.fields:
                    value = doc.azure_result.fields[field_name]
                    source = "azure"
                # Check Gemini results
                elif doc.gemini_result and field_name in doc.gemini_result.extracted_key_info:
                    value = doc.gemini_result.extracted_key_info[field_name]
                    source = "gemini"
                
                if value is not None:
                    field_values.append({
                        "document": doc.file_upload.filename,
                        "value": value,
                        "source": source
                    })
            
            # Analyze consistency
            unique_values = set(str(v["value"]) for v in field_values)
            is_consistent = len(unique_values) <= 1
            
            comparison_data.append({
                "field": field_name,
                "values": field_values,
                "is_consistent": is_consistent,
                "unique_count": len(unique_values)
            })
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            data={"comparisons": comparison_data}
        )
    
    async def _compare_documents(self, params: Dict[str, Any]) -> ToolResult:
        """Compare complete documents"""
        doc_names = params.get("document_names", [])
        
        if len(doc_names) < 2:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                data=None,
                error="Need at least 2 documents to compare"
            )
        
        # Find documents
        docs_to_compare = []
        for doc_name in doc_names:
            for doc in self.documents:
                if doc.file_upload.filename == doc_name:
                    docs_to_compare.append(doc)
                    break
        
        if len(docs_to_compare) < 2:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                data=None,
                error="Could not find all specified documents"
            )
        
        # Compare documents
        comparison = {
            "documents": doc_names,
            "common_fields": [],
            "differences": [],
            "unique_fields": {}
        }
        
        # Get all fields from all documents
        all_fields = set()
        doc_fields = {}
        
        for doc in docs_to_compare:
            fields = set()
            if doc.azure_result:
                fields.update(doc.azure_result.fields.keys())
            if doc.gemini_result:
                fields.update(doc.gemini_result.extracted_key_info.keys())
            
            doc_fields[doc.file_upload.filename] = fields
            all_fields.update(fields)
        
        # Find common and unique fields
        common_fields = set.intersection(*doc_fields.values())
        comparison["common_fields"] = list(common_fields)
        
        for doc_name, fields in doc_fields.items():
            unique = fields - common_fields
            if unique:
                comparison["unique_fields"][doc_name] = list(unique)
        
        # Compare values for common fields
        for field in common_fields:
            values = {}
            for doc in docs_to_compare:
                if doc.azure_result and field in doc.azure_result.fields:
                    values[doc.file_upload.filename] = doc.azure_result.fields[field]
                elif doc.gemini_result and field in doc.gemini_result.extracted_key_info:
                    values[doc.file_upload.filename] = doc.gemini_result.extracted_key_info[field]
            
            # Check if values differ
            unique_values = set(str(v) for v in values.values())
            if len(unique_values) > 1:
                comparison["differences"].append({
                    "field": field,
                    "values": values
                })
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            data=comparison
        )
    
    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="document_comparison",
            description="Compare data across documents",
            parameters={
                "type": "object",
                "properties": {
                    "comparison_type": {
                        "type": "string",
                        "enum": ["fields", "documents"],
                        "description": "Type of comparison"
                    },
                    "field_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Fields to compare (for field comparison)"
                    },
                    "document_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Documents to compare (for document comparison)"
                    }
                },
                "required": ["comparison_type"]
            },
            returns={
                "type": "object",
                "description": "Comparison results"
            }
        )


class ValidationReviewTool(BaseTool):
    """Tool for reviewing validation errors and data quality"""
    
    def __init__(self, documents: List[ProcessedDocument]):
        self.documents = documents
    
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """Review validation status and errors"""
        review_type = params.get("review_type", "summary")
        
        validation_data = {
            "total_documents": len(self.documents),
            "documents_with_errors": 0,
            "total_errors": 0,
            "error_breakdown": defaultdict(int),
            "document_details": []
        }
        
        for doc in self.documents:
            if doc.validation_errors:
                validation_data["documents_with_errors"] += 1
                validation_data["total_errors"] += len(doc.validation_errors)
                
                doc_errors = {
                    "document": doc.file_upload.filename,
                    "error_count": len(doc.validation_errors),
                    "errors": []
                }
                
                for error in doc.validation_errors:
                    validation_data["error_breakdown"][error.severity] += 1
                    doc_errors["errors"].append({
                        "field": error.field,
                        "message": error.message,
                        "severity": error.severity
                    })
                
                validation_data["document_details"].append(doc_errors)
        
        # Add processing status summary
        status_summary = defaultdict(int)
        for doc in self.documents:
            status_summary[doc.processing_status.value] += 1
        
        validation_data["processing_status_summary"] = dict(status_summary)
        
        # Prepare response based on review type
        if review_type == "summary":
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                data={
                    "total_documents": validation_data["total_documents"],
                    "documents_with_errors": validation_data["documents_with_errors"],
                    "total_errors": validation_data["total_errors"],
                    "error_severity_breakdown": dict(validation_data["error_breakdown"]),
                    "processing_status": validation_data["processing_status_summary"]
                }
            )
        else:  # detailed
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                data=validation_data
            )
    
    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="validation_review",
            description="Review validation errors and data quality",
            parameters={
                "type": "object",
                "properties": {
                    "review_type": {
                        "type": "string",
                        "enum": ["summary", "detailed"],
                        "description": "Level of detail for review"
                    }
                },
                "required": []
            },
            returns={
                "type": "object",
                "description": "Validation review results"
            }
        )


class MissingDataFinderTool(BaseTool):
    """Tool for identifying missing data and documents"""
    
    def __init__(self, documents: List[ProcessedDocument]):
        self.documents = documents
    
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """Find missing data and suggest required documents"""
        
        missing_data = {
            "missing_fields": [],
            "low_confidence_fields": [],
            "suggested_documents": [],
            "incomplete_documents": []
        }
        
        # Check each document for missing data
        for doc in self.documents:
            doc_missing = []
            
            if doc.azure_result:
                # Check for common required fields based on document type
                doc_type = doc.azure_result.doc_type.upper()
                
                if "W2" in doc_type or "W-2" in doc_type:
                    required_fields = [
                        "Employee_Name", "Employee_SocialSecurityNumber",
                        "Employer_Name", "Employer_IdNumber",
                        "WagesTipsAndOtherCompensation", "FederalIncomeTaxWithheld"
                    ]
                    
                    for field in required_fields:
                        if field not in doc.azure_result.fields or not doc.azure_result.fields[field]:
                            doc_missing.append(field)
                
                elif "1099" in doc_type:
                    # Basic required fields for most 1099s
                    required_fields = ["Payer_Name", "Payer_TIN", "Recipient_Name", "Recipient_TIN"]
                    
                    for field in required_fields:
                        if field not in doc.azure_result.fields or not doc.azure_result.fields[field]:
                            doc_missing.append(field)
                
                # Check confidence scores
                for field, value in doc.azure_result.fields.items():
                    # If field has confidence info (would need to be added to our model)
                    # For now, we'll flag empty fields
                    if value == "" or value is None:
                        missing_data["low_confidence_fields"].append({
                            "document": doc.file_upload.filename,
                            "field": field,
                            "reason": "empty_value"
                        })
            
            if doc_missing:
                missing_data["missing_fields"].extend([
                    {"document": doc.file_upload.filename, "field": field}
                    for field in doc_missing
                ])
                missing_data["incomplete_documents"].append(doc.file_upload.filename)
        
        # Suggest missing documents based on what we have
        doc_types_found = set()
        for doc in self.documents:
            if doc.azure_result:
                doc_types_found.add(doc.azure_result.doc_type.upper())
        
        # Basic suggestions
        if not any("W2" in dt or "W-2" in dt for dt in doc_types_found):
            missing_data["suggested_documents"].append({
                "document_type": "W-2",
                "reason": "No W-2 forms found - needed if client had employment income"
            })
        
        if not any("1099-INT" in dt for dt in doc_types_found):
            missing_data["suggested_documents"].append({
                "document_type": "1099-INT",
                "reason": "No 1099-INT found - check if client has bank accounts with interest"
            })
        
        # Add summary
        missing_data["summary"] = {
            "total_missing_fields": len(missing_data["missing_fields"]),
            "total_incomplete_documents": len(missing_data["incomplete_documents"]),
            "total_suggested_documents": len(missing_data["suggested_documents"])
        }
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            data=missing_data
        )
    
    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="missing_data_finder",
            description="Identify missing data and suggest required documents",
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            },
            returns={
                "type": "object",
                "description": "Missing data analysis"
            }
        )
