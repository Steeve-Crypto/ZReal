from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.utils import timezone
import pdfplumber
import pytesseract
from PIL import Image
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .forms import PropertyForm
from .models import Property, PropertyDocument, TokenizationOperation
from .serializers import document_payload, property_payload, tokenization_operation_payload
from .views import (
    _hash_uploaded_file,
    _issuer_operation_or_404,
    _issuer_property_or_404,
    _require_issuer,
    _safe_tokenization_metadata,
    _sync_property_from_operation,
    _extract_field,
)
from zcash_integration.zcash_client import ZcashClient, ZcashConfigurationError


def visible_property_queryset(user):
    public_qs = Property.objects.filter(status__in=["tokenized", "active"])
    if user.is_authenticated and getattr(user, "profile", None) and user.profile.is_issuer:
        return Property.objects.filter(owner=user) | public_qs
    return public_qs


@api_view(["GET"])
@permission_classes([AllowAny])
def property_list(request):
    properties = visible_property_queryset(request.user).distinct().prefetch_related("documents")
    return Response({"properties": [property_payload(prop, request.user) for prop in properties]})


@api_view(["GET"])
@permission_classes([AllowAny])
def investor_browse(request):
    properties = Property.objects.filter(status__in=["tokenized", "active"]).prefetch_related("documents")
    return Response({"properties": [property_payload(prop, request.user) for prop in properties]})


@api_view(["GET"])
@permission_classes([AllowAny])
def property_detail(request, pk):
    prop = get_object_or_404(visible_property_queryset(request.user).distinct().prefetch_related("documents"), pk=pk)
    payload = property_payload(prop, request.user)
    if request.user.is_authenticated and getattr(request.user, "profile", None) and prop.owner_id == request.user.id:
        payload["documents"] = [document_payload(doc) for doc in prop.documents.all()]
        payload["tokenization_operations"] = [
            tokenization_operation_payload(op, request.user)
            for op in prop.tokenization_operations.all()
        ]
    return Response(payload)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_property(request):
    _require_issuer(request.user)
    form = PropertyForm(request.data)
    if not form.is_valid():
        return Response({"errors": form.errors}, status=400)
    prop = form.save(commit=False)
    prop.owner = request.user
    prop.save()
    return Response(property_payload(prop, request.user), status=201)


@api_view(["PATCH", "PUT"])
@permission_classes([IsAuthenticated])
def edit_property(request, pk):
    prop = _issuer_property_or_404(request.user, pk)
    form = PropertyForm(request.data, instance=prop)
    if not form.is_valid():
        return Response({"errors": form.errors}, status=400)
    prop = form.save()
    return Response(property_payload(prop, request.user))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def property_documents(request, pk):
    prop = _issuer_property_or_404(request.user, pk)
    return Response({"documents": [document_payload(doc) for doc in prop.documents.order_by("-uploaded_at")]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_document(request, pk):
    prop = _issuer_property_or_404(request.user, pk)
    uploaded_file = request.FILES.get("document")
    if not uploaded_file:
        return Response({"error": "No document uploaded."}, status=400)
    allowed_extensions = (".pdf", ".png", ".jpg", ".jpeg")
    if not uploaded_file.name.lower().endswith(allowed_extensions):
        return Response({"error": "Only PDF, PNG, JPG, and JPEG documents are supported."}, status=400)
    if uploaded_file.size > 10 * 1024 * 1024:
        return Response({"error": "Document uploads are limited to 10 MB."}, status=400)

    doc = PropertyDocument.objects.create(
        property=prop,
        file=uploaded_file,
        document_type=request.data.get("document_type", "Legal Document"),
        file_sha256=_hash_uploaded_file(uploaded_file),
        processing_status="processing",
    )

    try:
        extracted_text = ""
        extracted_data = {}
        if uploaded_file.name.lower().endswith(".pdf"):
            with pdfplumber.open(doc.file.path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        extracted_text += text + "\n\n"
                    tables = page.extract_tables()
                    if tables:
                        extracted_data["tables"] = extracted_data.get("tables", []) + tables
        else:
            image = Image.open(doc.file.path)
            extracted_text = pytesseract.image_to_string(image)
            extracted_data["ocr_used"] = True

        extracted_data.update({
            "detected_address": _extract_field(extracted_text, r"(?i)(address|property located at)[:\s]+([^\n]+)"),
            "detected_size": _extract_field(extracted_text, r"(?i)(sqm|square meters|sq\.?\s?ft)[:\s]*([\d,\.]+)"),
            "detected_owner": _extract_field(extracted_text, r"(?i)(owner|grantor|seller)[:\s]+([^\n]+)"),
        })
        doc.extracted_text = extracted_text[:5000]
        doc.extracted_data = extracted_data
        doc.processing_status = "completed"
        doc.processed_at = timezone.now()
        doc.save()
        return Response(document_payload(doc), status=201)
    except Exception as exc:
        doc.processing_status = "failed"
        doc.save(update_fields=["processing_status"])
        return Response({"error": str(exc), "document": document_payload(doc)}, status=500)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def zsa_config_readiness(request):
    if not (request.user.is_staff or getattr(request.user, "profile", None) and request.user.profile.is_issuer):
        raise PermissionDenied("Only issuers or staff can validate ZSA configuration.")
    return Response(ZcashClient().configuration_report())


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def issue_property_tokenization(request, pk):
    prop = _issuer_property_or_404(request.user, pk)
    if settings.REQUIRE_ACTIVE_SUBSCRIPTION_FOR_ZSA and not request.user.profile.has_active_subscription:
        return Response({"error": "An active issuer subscription is required for tokenization."}, status=403)

    issuer_zaddr = request.data.get("issuer_zaddr", "").strip()
    if not issuer_zaddr:
        return Response({"error": "Issuer shielded address is required."}, status=400)

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
        status="pending",
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
        return Response(tokenization_operation_payload(operation, request.user), status=201)
    except (ZcashConfigurationError, ValueError, RuntimeError) as exc:
        operation.status = "failed"
        operation.error = str(exc)
        operation.failed_at = timezone.now()
        operation.save()
        prop.tokenization_status = "failed"
        prop.tokenization_error = str(exc)
        prop.save(update_fields=["tokenization_status", "tokenization_error", "updated_at"])
        return Response(tokenization_operation_payload(operation, request.user), status=400)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tokenization_operation_detail(request, pk):
    operation = _issuer_operation_or_404(request.user, pk)
    return Response(tokenization_operation_payload(operation, request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def refresh_tokenization_operation(request, pk):
    operation = _issuer_operation_or_404(request.user, pk)
    if not operation.operation_id:
        return Response({"error": "This tokenization operation has no operation ID to refresh."}, status=400)
    try:
        result = ZcashClient().refresh_zsa_status(operation.operation_id)
        operation.mark_from_result(result)
        _sync_property_from_operation(operation.property, operation)
        return Response(tokenization_operation_payload(operation, request.user))
    except (ZcashConfigurationError, ValueError, RuntimeError) as exc:
        operation.status = "failed"
        operation.error = str(exc)
        operation.failed_at = timezone.now()
        operation.save(update_fields=["status", "error", "failed_at", "updated_at"])
        _sync_property_from_operation(operation.property, operation)
        return Response(tokenization_operation_payload(operation, request.user), status=400)
