import hashlib
import json
import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied as DrfPermissionDenied

from .forms import PropertyForm
from .models import Property, PropertyDocument, TokenizationOperation
from .serializers import PropertySerializer  # Create this if using DRF
from zcash_integration.zcash_client import ZcashClient, ZcashConfigurationError


def _require_issuer(user):
    if not user.is_authenticated:
        raise PermissionDenied("Authentication is required.")
    profile = getattr(user, 'profile', None)
    if not profile or not profile.is_issuer:
        raise PermissionDenied("Only issuers can perform this action.")


def _issuer_property_or_404(user, pk):
    _require_issuer(user)
    return get_object_or_404(Property, pk=pk, owner=user)


def _hash_uploaded_file(uploaded_file):
    digest = hashlib.sha256()
    for chunk in uploaded_file.chunks():
        digest.update(chunk)
    uploaded_file.seek(0)
    return digest.hexdigest()


def _safe_tokenization_metadata(prop, asset_symbol):
    documents = []
    for doc in prop.documents.filter(processing_status='completed').order_by('-processed_at'):
        extracted_safe = {}
        for key in ['detected_address', 'detected_size']:
            value = (doc.extracted_data or {}).get(key)
            if value:
                extracted_safe[key] = value
        documents.append({
            'document_id': doc.id,
            'document_type': doc.document_type,
            'file_sha256': doc.file_sha256,
            'uploaded_at': doc.uploaded_at.isoformat() if doc.uploaded_at else None,
            'processed_at': doc.processed_at.isoformat() if doc.processed_at else None,
            'extracted_safe': extracted_safe,
        })

    return {
        'schema': 'zreal.tokenization.v1',
        'property_id': prop.id,
        'asset_symbol': asset_symbol,
        'total_shares': prop.total_shares,
        'generated_at': timezone.now().isoformat(),
        'documents': documents,
    }


def _masked_zaddr(address):
    if not address:
        return "No data yet"
    if len(address) <= 16:
        return f"{address[:4]}..."
    return f"{address[:8]}...{address[-6:]}"


def _sync_property_from_operation(prop, operation):
    prop.tokenization_status = operation.status
    prop.zcash_operation_id = operation.operation_id or prop.zcash_operation_id
    prop.zcash_txid = operation.txid or prop.zcash_txid
    prop.zsa_asset_id = operation.asset_id or prop.zsa_asset_id
    prop.tokenization_error = operation.error
    if operation.status in ['pending', 'broadcast']:
        prop.status = 'tokenizing'
    if operation.status == 'confirmed':
        prop.status = 'tokenized'
        prop.tokenized_at = operation.confirmed_at or timezone.now()
    prop.save()


def _issuer_operation_or_404(user, pk):
    if user.is_staff:
        return get_object_or_404(
            TokenizationOperation.objects.select_related('property', 'issuer'),
            pk=pk,
        )
    _require_issuer(user)
    return get_object_or_404(
        TokenizationOperation.objects.select_related('property', 'issuer'),
        pk=pk,
        issuer=user,
    )


def property_map(request):
    """Interactive map view using Leaflet + OSM (Google Maps free alternative)"""
    public_properties = Property.objects.filter(status__in=['tokenized', 'active']).order_by('-tokenized_at', '-created_at')
    issuer_only_properties = Property.objects.none()
    is_issuer = (
        request.user.is_authenticated
        and getattr(request.user, 'profile', None)
        and request.user.profile.is_issuer
    )
    if is_issuer:
        issuer_only_properties = Property.objects.filter(owner=request.user).exclude(
            status__in=['tokenized', 'active']
        ).order_by('-created_at')

    properties = list(public_properties[:50])
    issuer_only_list = list(issuer_only_properties[:50])
    visible_properties = properties + issuer_only_list
    properties_json = []

    for prop in visible_properties:
        is_public = prop.status in ['tokenized', 'active']
        properties_json.append({
            'id': prop.id,
            'title': prop.title,
            'address': prop.address,
            'lat': float(prop.latitude) if prop.latitude is not None else None,
            'lng': float(prop.longitude) if prop.longitude is not None else None,
            'size_sqm': prop.size_sqm,
            'estimated_value': f"${prop.estimated_value:,.2f}" if prop.estimated_value else None,
            'status': prop.get_status_display(),
            'status_key': prop.status,
            'visibility': 'public' if is_public else 'issuer_only',
            'visibility_label': 'Public' if is_public else 'Issuer-only draft',
            'total_shares': prop.total_shares,
            'zsa_asset_id': prop.zsa_asset_id[:20] if prop.zsa_asset_id else None,
        })

    return render(request, 'properties/map.html', {
        'properties': visible_properties,
        'public_properties': properties,
        'issuer_only_properties': issuer_only_list,
        'has_public_properties': bool(properties),
        'has_issuer_only_properties': bool(issuer_only_list),
        'is_issuer_map': is_issuer,
        'map_center_json': '[39.8283, -98.5795]',
        'properties_json': properties_json,
    })


def investor_property_browse(request):
    """Browse only tokenized or active properties available to investors."""
    properties = Property.objects.filter(status__in=['tokenized', 'active']).order_by('-tokenized_at', '-created_at')
    return render(request, 'properties/browse.html', {'properties': properties})


@login_required
def property_create(request):
    _require_issuer(request.user)
    form = PropertyForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        prop = form.save(commit=False)
        prop.owner = request.user
        prop.save()
        messages.success(request, "Property created.")
        return redirect('issuer_dashboard')
    return render(request, 'properties/property_form.html', {'form': form, 'mode': 'Create'})


@login_required
def property_edit(request, pk):
    prop = _issuer_property_or_404(request.user, pk)
    form = PropertyForm(request.POST or None, instance=prop)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Property updated.")
        return redirect('issuer_dashboard')
    return render(request, 'properties/property_form.html', {'form': form, 'mode': 'Edit', 'property': prop})


@login_required
@require_POST
def issue_zsa_example(request, pk):
    """Issue a real ZSA using the configured ZSA backend/tool."""
    prop = _issuer_property_or_404(request.user, pk)
    if settings.REQUIRE_ACTIVE_SUBSCRIPTION_FOR_ZSA and not request.user.profile.has_active_subscription:
        messages.error(request, "An active issuer subscription is required for tokenization.")
        return redirect('issuer_dashboard')

    issuer_zaddr = request.POST.get('issuer_zaddr', '').strip()
    if not issuer_zaddr:
        messages.error(request, "Issuer shielded address is required.")
        return redirect('issuer_dashboard')

    asset_symbol = f"ZREAL-PROP-{prop.id}"
    metadata = _safe_tokenization_metadata(prop, asset_symbol)
    operation = TokenizationOperation.objects.create(
        property=prop,
        issuer=request.user,
        issuer_zaddr=issuer_zaddr,
        asset_symbol=asset_symbol,
        total_shares=prop.total_shares,
        backend=settings.ZSA_ISSUANCE_BACKEND,
        metadata=metadata,
        status='pending',
    )

    try:
        result = ZcashClient().issue_zsa(
            issuer_zaddr=issuer_zaddr,
            asset_symbol=operation.asset_symbol,
            total_shares=prop.total_shares,
            metadata=metadata,
        )
        operation.mark_from_result(result)

        _sync_property_from_operation(prop, operation)
        messages.success(request, "Tokenization request submitted to the configured ZSA backend.")
    except (ZcashConfigurationError, ValueError, RuntimeError) as exc:
        operation.status = 'failed'
        operation.error = str(exc)
        operation.failed_at = timezone.now()
        operation.save()
        prop.tokenization_status = 'failed'
        prop.tokenization_error = str(exc)
        prop.save(update_fields=['tokenization_status', 'tokenization_error', 'updated_at'])
        messages.error(request, f"Tokenization failed: {exc}")

    return redirect('issuer_dashboard')


@login_required
@require_POST
def refresh_zsa_status(request, pk):
    prop = _issuer_property_or_404(request.user, pk)
    operation = prop.tokenization_operations.first()
    if not operation:
        messages.error(request, "No tokenization operation exists for this property.")
        return redirect('issuer_dashboard')
    if not operation.operation_id:
        messages.error(request, "This tokenization operation has no operation ID to refresh.")
        return redirect('issuer_dashboard')

    try:
        result = ZcashClient().refresh_zsa_status(operation.operation_id)
        operation.mark_from_result(result)
        _sync_property_from_operation(prop, operation)
        messages.success(request, "Tokenization status refreshed.")
    except (ZcashConfigurationError, ValueError, RuntimeError) as exc:
        operation.status = 'failed'
        operation.error = str(exc)
        operation.failed_at = timezone.now()
        operation.save()
        prop.tokenization_status = 'failed'
        prop.tokenization_error = str(exc)
        prop.save(update_fields=['tokenization_status', 'tokenization_error', 'updated_at'])
        messages.error(request, f"Status refresh failed: {exc}")
    return redirect('issuer_dashboard')


@login_required
def tokenization_operation_detail(request, pk):
    operation = _issuer_operation_or_404(request.user, pk)
    context = {
        'operation': operation,
        'property': operation.property,
        'issuer_zaddr_masked': _masked_zaddr(operation.issuer_zaddr),
        'metadata_pretty': json.dumps(operation.metadata or {}, indent=2, sort_keys=True),
        'response_pretty': json.dumps(operation.response or {}, indent=2, sort_keys=True),
        'can_refresh': bool(operation.operation_id and operation.status in ['pending', 'broadcast', 'failed']),
    }
    return render(request, 'properties/tokenization_operation_detail.html', context)


@login_required
@require_POST
def refresh_tokenization_operation(request, pk):
    operation = _issuer_operation_or_404(request.user, pk)
    if not operation.operation_id:
        messages.error(request, "This tokenization operation has no operation ID to refresh.")
        return redirect('tokenization_operation_detail', pk=operation.pk)

    try:
        result = ZcashClient().refresh_zsa_status(operation.operation_id)
        operation.mark_from_result(result)
        _sync_property_from_operation(operation.property, operation)
        messages.success(request, "Tokenization operation status refreshed.")
    except (ZcashConfigurationError, ValueError, RuntimeError) as exc:
        operation.status = 'failed'
        operation.error = str(exc)
        operation.failed_at = timezone.now()
        operation.save(update_fields=['status', 'error', 'failed_at', 'updated_at'])
        _sync_property_from_operation(operation.property, operation)
        messages.error(request, f"Status refresh failed: {exc}")

    return redirect('tokenization_operation_detail', pk=operation.pk)


@login_required
def validate_zsa_configuration(request):
    if not (request.user.is_staff or getattr(request.user, 'profile', None) and request.user.profile.is_issuer):
        raise PermissionDenied("Only issuers or staff can validate ZSA configuration.")
    return JsonResponse(ZcashClient().configuration_report())


@login_required
def generate_sapling_address_view(request):
    """
    Utility endpoint to generate a new Sapling shielded address.
    Useful during testing and for new users/issuers.
    """
    client = ZcashClient()
    address_type = request.GET.get('type', 'sapling')
    try:
        result = client.generate_sapling_address(address_type)
        return JsonResponse({"address": result})
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=400)

class PropertyViewSet(viewsets.ModelViewSet):
    serializer_class = PropertySerializer  # Define in serializers.py

    def get_queryset(self):
        if self.request.user.is_authenticated and getattr(self.request.user, 'profile', None):
            if self.request.user.profile.is_issuer:
                return Property.objects.filter(owner=self.request.user)
        return Property.objects.filter(status__in=['tokenized', 'active'])

    def perform_create(self, serializer):
        if not getattr(self.request.user, 'profile', None) or not self.request.user.profile.is_issuer:
            raise DrfPermissionDenied("Only issuers can create properties.")
        serializer.save(owner=self.request.user)

# ==================== DOCUMENT INTELLIGENCE (Legal Shield) ====================

import pytesseract
import pdfplumber
from PIL import Image

@login_required
def upload_property_document(request, pk):
    """Upload and process a document for a property using pdfplumber + OCR."""
    if request.method != 'POST':
        return JsonResponse({"error": "POST required"}, status=405)
    
    prop = _issuer_property_or_404(request.user, pk)
    
    if 'document' not in request.FILES:
        return JsonResponse({"error": "No document uploaded"}, status=400)
    
    uploaded_file = request.FILES['document']
    allowed_extensions = ('.pdf', '.png', '.jpg', '.jpeg')
    if not uploaded_file.name.lower().endswith(allowed_extensions):
        return JsonResponse({"error": "Only PDF, PNG, JPG, and JPEG documents are supported."}, status=400)
    if uploaded_file.size > 10 * 1024 * 1024:
        return JsonResponse({"error": "Document uploads are limited to 10 MB."}, status=400)
    file_sha256 = _hash_uploaded_file(uploaded_file)
    doc_type = request.POST.get('document_type', 'Legal Document')
    
    # Save the document
    doc = PropertyDocument.objects.create(
        property=prop,
        file=uploaded_file,
        document_type=doc_type,
        file_sha256=file_sha256,
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
            except Exception as exc:
                raise ValueError(f"Could not extract text from this file type: {exc}") from exc
        
        # Simple field extraction (can be greatly improved with regex/LLM)
        extracted_data.update({
            'detected_address': _extract_field(extracted_text, r'(?i)(address|property located at)[:\s]+([^\n]+)'),
            'detected_size': _extract_field(extracted_text, r'(?i)(sqm|square meters|sq\.?\s?ft)[:\s]*([\d,\.]+)'),
            'detected_owner': _extract_field(extracted_text, r'(?i)(owner|grantor|seller)[:\s]+([^\n]+)'),
        })
        
        # Update document
        doc.extracted_text = extracted_text[:5000]  # Limit size
        doc.extracted_data = extracted_data
        doc.ocr_confidence = None
        doc.processing_status = 'completed'
        doc.processed_at = timezone.now()
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
    match = re.search(pattern, text)
    return match.group(2).strip() if match else None
