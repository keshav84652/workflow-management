"""
Fixed Income Aggregation Tool for CPA Copilot
This version properly handles the nested Azure transaction data structure.
"""

from typing import Dict, Any, List, Optional
from collections import defaultdict

def extract_numeric_value(value: Any) -> float:
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

def extract_income_from_azure_transactions(azure_fields: Dict[str, Any], doc_type: str) -> Optional[float]:
    """
    Extract income from Azure transaction data structure
    """
    transactions = azure_fields.get("Transactions", [])
    if not transactions or not isinstance(transactions, list):
        return None
    
    transaction = transactions[0]  # Get first transaction
    
    if "INT" in doc_type.upper():
        # For 1099-INT: Box1 is interest income
        return extract_numeric_value(transaction.get("Box1", 0))
    
    elif "DIV" in doc_type.upper():
        # For 1099-DIV: Box1a is ordinary dividends, fallback to Box1
        return extract_numeric_value(
            transaction.get("Box1a", transaction.get("Box1", 0))
        )
    
    elif "G" in doc_type.upper():
        # For 1099-G: Box1 is unemployment compensation or state/local tax refunds
        return extract_numeric_value(transaction.get("Box1", 0))
    
    elif "NEC" in doc_type.upper():
        # For 1099-NEC: Box1 is nonemployee compensation
        return extract_numeric_value(transaction.get("Box1", 0))
    
    elif "MISC" in doc_type.upper():
        # For 1099-MISC: Can be in various boxes, try common ones
        for box in ["Box1", "Box3", "Box7"]:
            value = extract_numeric_value(transaction.get(box, 0))
            if value > 0:
                return value
    
    return None

def aggregate_income_fixed(documents: List) -> Dict[str, Any]:
    """
    Fixed income aggregation logic
    """
    income_data = defaultdict(float)
    document_breakdown = []
    
    print(f"Processing {len(documents)} documents for income aggregation...")
    
    for i, doc in enumerate(documents):
        print(f"Document {i+1}: {doc.file_upload.filename}")
        
        # Try Azure results first
        if doc.azure_result and doc.azure_result.doc_type and doc.azure_result.fields:
            doc_type = doc.azure_result.doc_type.upper()
            print(f"   Azure doc type: {doc_type}")
            
            # W-2 Income
            if "W2" in doc_type or "W-2" in doc_type:
                wages = extract_numeric_value(
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
                    print(f"   Found W-2 wages: ${wages:,.2f}")
            
            # 1099 Income - USE FIXED EXTRACTION
            elif "1099" in doc_type:
                # Try the new transaction-based extraction
                income_amount = extract_income_from_azure_transactions(
                    doc.azure_result.fields, doc_type
                )
                
                if income_amount and income_amount > 0:
                    # Categorize based on 1099 type
                    if "INT" in doc_type:
                        income_data["interest"] += income_amount
                        category = "interest"
                        form_type = "1099-INT"
                        print(f"   Found 1099-INT interest: ${income_amount:,.2f}")
                    elif "DIV" in doc_type:
                        income_data["dividends"] += income_amount
                        category = "dividends"
                        form_type = "1099-DIV"
                        print(f"   Found 1099-DIV dividends: ${income_amount:,.2f}")
                    elif "G" in doc_type:
                        income_data["other"] += income_amount
                        category = "other"
                        form_type = "1099-G"
                        print(f"   Found 1099-G income: ${income_amount:,.2f}")
                    elif "NEC" in doc_type:
                        income_data["self_employment"] += income_amount
                        category = "self_employment"
                        form_type = "1099-NEC"
                        print(f"   Found 1099-NEC income: ${income_amount:,.2f}")
                    else:
                        income_data["other"] += income_amount
                        category = "other"
                        form_type = doc_type
                        print(f"   Found other 1099 income: ${income_amount:,.2f}")
                    
                    document_breakdown.append({
                        "document": doc.file_upload.filename,
                        "type": form_type,
                        "category": category,
                        "amount": income_amount
                    })
                else:
                    print(f"   No income found in Azure transaction data")
        
        # If no Azure income found, try Gemini results
        if not any(b["document"] == doc.file_upload.filename for b in document_breakdown):
            if doc.gemini_result and doc.gemini_result.extracted_key_info:
                gemini_data = doc.gemini_result.extracted_key_info
                form_type = gemini_data.get("form_type", "").upper()
                print(f"   📋 Gemini form type: {form_type}")
                
                # Extract income based on form type
                if "W-2" in form_type or "W2" in form_type:
                    wages = extract_numeric_value(gemini_data.get("box1", 0))
                    if wages > 0:
                        income_data["wages"] += wages
                        document_breakdown.append({
                            "document": doc.file_upload.filename,
                            "type": "W-2",
                            "category": "wages",
                            "amount": wages
                        })
                        print(f"   Found Gemini W-2 wages: ${wages:,.2f}")
                
                elif "1099" in form_type:
                    if "INT" in form_type:
                        interest = extract_numeric_value(gemini_data.get("box1", 0))
                        if interest > 0:
                            income_data["interest"] += interest
                            document_breakdown.append({
                                "document": doc.file_upload.filename,
                                "type": "1099-INT",
                                "category": "interest",
                                "amount": interest
                            })
                            print(f"   Found Gemini 1099-INT interest: ${interest:,.2f}")
                    
                    elif "DIV" in form_type:
                        dividends = extract_numeric_value(
                            gemini_data.get("box1a", gemini_data.get("box1", 0))
                        )
                        if dividends > 0:
                            income_data["dividends"] += dividends
                            document_breakdown.append({
                                "document": doc.file_upload.filename,
                                "type": "1099-DIV",
                                "category": "dividends",
                                "amount": dividends
                            })
                            print(f"   Found Gemini 1099-DIV dividends: ${dividends:,.2f}")
                    
                    elif "G" in form_type:
                        govt_payments = extract_numeric_value(gemini_data.get("box1", 0))
                        if govt_payments > 0:
                            income_data["other"] += govt_payments
                            document_breakdown.append({
                                "document": doc.file_upload.filename,
                                "type": "1099-G",
                                "category": "other",
                                "amount": govt_payments
                            })
                            print(f"   Found Gemini 1099-G income: ${govt_payments:,.2f}")
                    
                    # Generic 1099 handling
                    else:
                        amount = extract_numeric_value(
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
                            print(f"   Found Gemini generic income: ${amount:,.2f}")
        
        if not any(b["document"] == doc.file_upload.filename for b in document_breakdown):
            print(f"   No income found for this document")
    
    # Calculate totals
    total_income = sum(income_data.values())
    
    print(f"\nINCOME SUMMARY")
    print(f"Total Income: ${total_income:,.2f}")
    for category, amount in income_data.items():
        print(f"  {category.title()}: ${amount:,.2f}")
    
    return {
        "total_income": total_income,
        "income_by_category": dict(income_data),
        "document_breakdown": document_breakdown,
        "document_count": len(document_breakdown)
    }

# Test function to verify the fix
def test_income_extraction():
    """Test the income extraction with sample data"""
    
    # Sample Azure transaction data structure (from chat history)
    sample_azure_fields = {
        'TaxYear': '2023',
        'Payer_Name': 'CONTOSO BANK',
        'Transactions': [{
            'Box1': 123456,  # Interest income
            'Box2': 54321,   # Early withdrawal penalty
            'Box4': 987,     # Federal tax withheld
            'Box5': 963,
            'Box6': 753
        }]
    }
    
    # Test extraction
    doc_type = "tax.us.1099INT.2022"
    income = extract_income_from_azure_transactions(sample_azure_fields, doc_type)
    
    print(f"TEST RESULTS")
    print(f"Document Type: {doc_type}")
    print(f"Extracted Income: ${income:,.2f}" if income else "No income extracted")
    print(f"Expected: $123,456.00")
    print(f"Test {'PASSED' if income == 123456 else 'FAILED'}")

if __name__ == "__main__":
    test_income_extraction()
