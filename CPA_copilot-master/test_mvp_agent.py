"""
Test script to verify MVP agent functionality
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent))

from backend.agents import TaxDocumentAnalystAgent
from backend.models.document import ProcessedDocument, FileUpload, AzureExtractionResult, ProcessingStatus
from datetime import datetime


def create_mock_documents():
    """Create mock processed documents for testing."""
    
    # Mock W-2 document
    w2_file = FileUpload(
        filename="w2_john_doe.pdf",
        content_type="application/pdf",
        size=1024,
        file_path=Path("mock_w2.pdf")
    )
    
    w2_azure_result = AzureExtractionResult(
        doc_type="W-2",
        confidence=0.95,
        fields={
            "Employee_Name": "John Doe",
            "Employee_SocialSecurityNumber": "123-45-6789",
            "Employer_Name": "ABC Corporation",
            "Employer_IdNumber": "12-3456789",
            "WagesTipsAndOtherCompensation": "75000.00",
            "FederalIncomeTaxWithheld": "12000.00"
        }
    )
    
    w2_doc = ProcessedDocument(
        file_upload=w2_file,
        azure_result=w2_azure_result,
        processing_status=ProcessingStatus.COMPLETED
    )
    
    # Mock 1099-INT document
    int_file = FileUpload(
        filename="1099_int_bank.pdf",
        content_type="application/pdf",
        size=512,
        file_path=Path("mock_1099_int.pdf")
    )
    
    int_azure_result = AzureExtractionResult(
        doc_type="1099-INT",
        confidence=0.88,
        fields={
            "Payer_Name": "First National Bank",
            "Payer_TIN": "98-7654321",
            "Recipient_Name": "John Doe",
            "Recipient_TIN": "123-45-6789",
            "InterestIncome": "1250.00"
        }
    )
    
    int_doc = ProcessedDocument(
        file_upload=int_file,
        azure_result=int_azure_result,
        processing_status=ProcessingStatus.COMPLETED
    )
    
    return [w2_doc, int_doc]


async def test_mvp_agent():
    """Test the MVP agent functionality."""
    print("🧪 Testing MVP Agent Functionality")
    print("=" * 50)
    
    # Create mock documents
    documents = create_mock_documents()
    print(f"✅ Created {len(documents)} mock documents")
    
    # Initialize agent
    agent = TaxDocumentAnalystAgent(documents)
    print(f"✅ Initialized agent with {len(agent.tool_registry.list_tools())} tools")
    print(f"   Available tools: {', '.join(agent.tool_registry.list_tools())}")
    
    # Test cases
    test_cases = [
        "What is my total income?",
        "Show me all wages from W-2 forms",
        "Are there any validation errors?",
        "Compare the SSN across all documents",
        "What information is missing?"
    ]
    
    print("\n🤖 Testing Agent Responses:")
    print("-" * 30)
    
    for i, test_message in enumerate(test_cases, 1):
        print(f"\n{i}. User: {test_message}")
        try:
            response = await agent.process_message(test_message)
            print(f"   Agent: {response.message}")
            
            if response.tool_results:
                print(f"   Tools used: {len(response.tool_results)} tool(s)")
                for tr in response.tool_results:
                    print(f"   - Status: {tr.status.value}")
            
            if response.suggested_actions:
                print(f"   Suggestions: {', '.join(response.suggested_actions[:2])}...")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    print("\n" + "=" * 50)
    print("✅ MVP Agent Test Complete!")
    
    # Test individual tools
    print("\n🔧 Testing Individual Tools:")
    print("-" * 30)
    
    # Test income aggregator
    try:
        income_result = await agent.execute_tool("income_aggregator", {"aggregation_type": "detailed"})
        if income_result.status.value == "success":
            total_income = income_result.data.get("total_income", 0)
            print(f"✅ Income Aggregator: Total income = ${total_income:,.2f}")
        else:
            print(f"❌ Income Aggregator failed: {income_result.error}")
    except Exception as e:
        print(f"❌ Income Aggregator error: {str(e)}")
    
    # Test validation review
    try:
        validation_result = await agent.execute_tool("validation_review", {"review_type": "summary"})
        if validation_result.status.value == "success":
            total_docs = validation_result.data.get("total_documents", 0)
            errors = validation_result.data.get("total_errors", 0)
            print(f"✅ Validation Review: {total_docs} documents, {errors} errors")
        else:
            print(f"❌ Validation Review failed: {validation_result.error}")
    except Exception as e:
        print(f"❌ Validation Review error: {str(e)}")
    
    # Test document inquiry
    try:
        inquiry_result = await agent.execute_tool("document_inquiry", {
            "query_type": "field",
            "field_name": "WagesTipsAndOtherCompensation"
        })
        if inquiry_result.status.value == "success":
            count = inquiry_result.data.get("count", 0)
            print(f"✅ Document Inquiry: Found {count} wage field(s)")
        else:
            print(f"❌ Document Inquiry failed: {inquiry_result.error}")
    except Exception as e:
        print(f"❌ Document Inquiry error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(test_mvp_agent())