from django.shortcuts import render
from django.http import JsonResponse
from rest_framework import viewsets
from .models import Property, PropertyInvestment
from .serializers import PropertySerializer  # Create this if using DRF
from zcash_integration.zcash_client import ZcashClient

def property_map(request):
    """Interactive map view using Leaflet + OSM (Google Maps free alternative)"""
    properties = Property.objects.all()[:50]  # Limit for demo
    return render(request, 'properties/map.html', {
        'properties': properties,
        'map_center': [51.505, -0.09],  # Default London example
    })

def issue_zsa_example(request, pk):
    """
    Full ZSA Issuance endpoint.
    Creates a shielded transaction that records the property tokenization on Zcash.
    """
    prop = Property.objects.get(pk=pk)
    client = ZcashClient()
    
    # Get issuer shielded address from POST or user profile (in real app)
    issuer_zaddr = request.POST.get('issuer_zaddr') or request.GET.get('issuer_zaddr')
    if not issuer_zaddr:
        return JsonResponse({"error": "issuer_zaddr (shielded z-address) is required"}, status=400)
    
    result = client.create_zsa_issuance_tx(
        issuer_zaddr=issuer_zaddr,
        property_id=prop.id,
        total_shares=prop.total_shares,
        asset_symbol=f"ZREAL-PROP-{prop.id}"
    )
    
    # Update property status
    if result.get("tx_result", {}).get("result"):
        prop.status = 'tokenizing'
        prop.zsa_asset_id = result["tx_result"]["result"]  # txid
        prop.save()
    
    return JsonResponse(result)


def distribute_rental_income(request, pk):
    """
    Shielded distribution flow example.
    Distributes rental income (or dividends) to ZSA token holders privately.
    """
    prop = Property.objects.get(pk=pk)
    client = ZcashClient()
    
    from_zaddr = request.POST.get('from_zaddr')
    if not from_zaddr:
        return JsonResponse({"error": "from_zaddr (issuer shielded address) required"}, status=400)
    
    # Example recipients - in production pull from PropertyInvestment model + user z-addresses
    # For demo we accept JSON in POST
    import json as json_module
    recipients_json = request.POST.get('recipients')
    if not recipients_json:
        return JsonResponse({"error": "recipients JSON required: [{'zaddr':.., 'amount':.., 'investor_id':..}, ...]"}, status=400)
    
    try:
        recipients = json_module.loads(recipients_json)
    except:
        return JsonResponse({"error": "Invalid recipients JSON"}, status=400)
    
    memo_base = {
        "property_id": prop.id,
        "distribution_type": "rental_income",
        "period": request.POST.get('period', '2026-Q2')
    }
    
    results = client.distribute_shielded_payments(
        from_zaddr=from_zaddr,
        recipients=recipients,
        memo_base=memo_base
    )
    
    return JsonResponse({"distribution_results": results, "property": prop.title})


def generate_sapling_address_view(request):
    """
    Utility endpoint to generate a new Sapling shielded address.
    Useful during testing and for new users/issuers.
    """
    client = ZcashClient()
    address_type = request.GET.get('type', 'sapling')
    result = client.generate_sapling_address(address_type)
    return JsonResponse(result)

class PropertyViewSet(viewsets.ModelViewSet):
    queryset = Property.objects.all()
    serializer_class = PropertySerializer  # Define in serializers.py
    permission_classes = []  # Adjust for production


# ==================== DOCUMENT INTELLIGENCE (Legal Shield) ====================

import pdfplumber
import pytesseract
from PIL import Image
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import json as json_lib
from datetime import datetime

@login_required
def upload_property_document(request, pk):
    """Upload and process a document for a property using pdfplumber + OCR."""
    if request.method != 'POST':
        return JsonResponse({"error": "POST required"}, status=405)
    
    prop = Property.objects.get(pk=pk)
    
    if 'document' not in request.FILES:
        return JsonResponse({"error": "No document uploaded"}, status=400)
    
    uploaded_file = request.FILES['document']
    doc_type = request.POST.get('document_type', 'Legal Document')
    
    # Save the document
    doc = PropertyDocument.objects.create(
        property=prop,
        file=uploaded_file,
        document_type=doc_type,
        processing_status='processing'
    )
    
    try:
        file_path = doc.file.path
        extracted_text = ""
        extracted_data = {}
        
        # Process PDF
        if uploaded_file.name.lower().endswith('.pdf'):
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        extracted_text += text + "\n\n"
                    
                    # Try to extract tables
                    tables = page.extract_tables()
                    if tables:
                        extracted_data['tables'] = extracted_data.get('tables', []) + tables
        
        # OCR fallback for images or scanned PDFs
        else:
            try:
                image = Image.open(file_path)
                extracted_text = pytesseract.image_to_string(image)
                extracted_data['ocr_used'] = True
            except:
                extracted_text = "Could not extract text from this file type."
        
        # Simple field extraction (can be greatly improved with regex/LLM)
        extracted_data.update({
            'detected_address': _extract_field(extracted_text, r'(?i)(address|property located at)[:\s]+([^\n]+)'),
            'detected_size': _extract_field(extracted_text, r'(?i)(sqm|square meters|sq\.?\s?ft)[:\s]*([\d,\.]+)'),
            'detected_owner': _extract_field(extracted_text, r'(?i)(owner|grantor|seller)[:\s]+([^\n]+)'),
        })
        
        # Update document
        doc.extracted_text = extracted_text[:5000]  # Limit size
        doc.extracted_data = extracted_data
        doc.ocr_confidence = 0.85  # Placeholder
        doc.processing_status = 'completed'
        doc.processed_at = datetime.now()
        doc.save()
        
        return JsonResponse({
            "success": True,
            "document_id": doc.id,
            "extracted_data": extracted_data,
            "message": "Document processed successfully with Legal Shield"
        })
        
    except Exception as e:
        doc.processing_status = 'failed'
        doc.save()
        return JsonResponse({"error": str(e)}, status=500)


def _extract_field(text, pattern):
    """Simple regex-based field extractor."""
    import re
    match = re.search(pattern, text)
    return match.group(2).strip() if match else None
