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

from core.notifications import push_notification
from .forms import PropertyForm
from .lifecycle import (
    PUBLIC_PROPERTY_STATUSES,
    active_subscription_required,
    can_attempt_tokenization,
    can_enrich_property,
    can_edit_property,
    can_upload_documents,
    evaluate_property_readiness,
    set_property_status,
    sync_pre_tokenization_lifecycle,
    sync_property_from_operation,
)
from .enrichment import (
    ProviderDisabled,
    ProviderMissingConfiguration,
    ProviderUnsupported,
    PropertyDataProviderError,
    enrichment_to_payload,
    resolve_property_address,
    status_for_result,
    store_reviewable_candidate,
    store_enrichment_result,
)
from .models import Property, PropertyDocument, PropertyEnrichment, TokenizationOperation
from .serializers import document_payload, property_payload, tokenization_operation_payload
from .views import (
    _hash_uploaded_file,
    _issuer_operation_or_404,
    _issuer_property_or_404,
    _require_issuer,
    _safe_tokenization_metadata,
    _extract_field,
)
from zcash_integration.zcash_client import ZcashClient, ZcashConfigurationError


def visible_property_queryset(user):
    public_qs = Property.objects.filter(status__in=PUBLIC_PROPERTY_STATUSES)
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
    properties = Property.objects.filter(status__in=PUBLIC_PROPERTY_STATUSES).prefetch_related("documents")
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
    candidate = request.data.get("enrichment_candidate")
    if isinstance(candidate, dict):
        store_reviewable_candidate(
            prop,
            provider=request.data.get("enrichment_provider", ""),
            candidate_data=candidate,
            candidates=request.data.get("enrichment_candidates") if isinstance(request.data.get("enrichment_candidates"), list) else None,
            status=request.data.get("enrichment_status", "needs_review"),
            warnings=request.data.get("enrichment_warnings") if isinstance(request.data.get("enrichment_warnings"), list) else [],
            blockers=request.data.get("enrichment_blockers") if isinstance(request.data.get("enrichment_blockers"), list) else [],
        )
    notification = push_notification(request, "success", "Property draft created.")
    return Response({"property": property_payload(prop, request.user), "notifications": [notification]}, status=201)


@api_view(["PATCH", "PUT"])
@permission_classes([IsAuthenticated])
def edit_property(request, pk):
    prop = _issuer_property_or_404(request.user, pk)
    if not can_edit_property(prop):
        code = "property_archived" if prop.status == "archived" else "invalid_lifecycle_state"
        return Response({"error": "Property cannot be edited in its current lifecycle state.", "code": code}, status=409)
    form = PropertyForm(request.data, instance=prop)
    if not form.is_valid():
        return Response({"errors": form.errors}, status=400)
    prop = form.save()
    transition = sync_pre_tokenization_lifecycle(prop, user=request.user)
    notifications = [push_notification(request, "success", "Property updated.")]
    if transition:
        notifications.append(push_notification(request, "success", transition.message))
    return Response({"property": property_payload(prop, request.user), "notifications": notifications})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def resolve_address(request):
    _require_issuer(request.user)
    address = (request.data.get("address") or "").strip()
    if not address:
        return Response({"error": "Address is required."}, status=400)
    try:
        result = resolve_property_address(address)
    except ProviderUnsupported as exc:
        return Response({"status": "failed", "warnings": ["Address provider is not supported."], "code": exc.code}, status=200)
    except ProviderMissingConfiguration as exc:
        return Response({"status": "failed", "warnings": ["Address provider is not configured."], "code": exc.code}, status=200)
    except ProviderDisabled as exc:
        return Response({"status": "failed", "warnings": ["Address provider is not enabled."], "code": exc.code}, status=200)
    except PropertyDataProviderError as exc:
        return Response({"status": "failed", "warnings": ["Address lookup is temporarily unavailable."], "code": exc.code}, status=200)
    return Response({
        "status": status_for_result(result),
        "provider": result.provider,
        "candidates": [candidate.to_safe_dict() for candidate in result.candidates],
        "warnings": result.warnings,
        "blockers": result.blockers,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def enrich_property(request, pk):
    prop = _issuer_property_or_404(request.user, pk)
    if not can_enrich_property(prop):
        return Response({"error": "Property cannot be enriched in its current lifecycle state.", "code": "invalid_lifecycle_state"}, status=409)
    address = (request.data.get("address") or prop.address or "").strip()
    if not address:
        return Response({"error": "Address is required."}, status=400)
    try:
        result = resolve_property_address(address)
        enrichment = store_enrichment_result(prop, result)
    except (ProviderUnsupported, ProviderMissingConfiguration, ProviderDisabled, PropertyDataProviderError) as exc:
        enrichment = prop.enrichment if hasattr(prop, "enrichment") else None
        if not enrichment:
            enrichment = PropertyEnrichment.objects.create(property=prop)
        enrichment.status = "failed"
        enrichment.provider = getattr(exc, "provider", "") or ""
        if isinstance(exc, ProviderUnsupported):
            warning = "Address provider is not supported."
        elif isinstance(exc, ProviderMissingConfiguration):
            warning = "Address provider is not configured."
        elif isinstance(exc, ProviderDisabled):
            warning = "Address provider is not enabled."
        else:
            warning = "Address lookup is temporarily unavailable."
        enrichment.warnings = [warning]
        enrichment.blockers = []
        enrichment.retrieved_at = timezone.now()
        enrichment.save()
    notification = push_notification(request, "success" if enrichment.status in ["enriched", "needs_review"] else "warning", "Property data enrichment updated.")
    return Response({
        "property": property_payload(prop, request.user),
        "enrichment": enrichment_to_payload(enrichment),
        "notifications": [notification],
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def property_enrichment(request, pk):
    prop = _issuer_property_or_404(request.user, pk)
    return Response(enrichment_to_payload(getattr(prop, "enrichment", None)))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def confirm_enrichment(request, pk):
    prop = _issuer_property_or_404(request.user, pk)
    if not can_enrich_property(prop):
        return Response({"error": "Property cannot be changed in its current lifecycle state.", "code": "invalid_lifecycle_state"}, status=409)
    enrichment = getattr(prop, "enrichment", None)
    if not enrichment or enrichment.status == "not_started":
        return Response({"error": "No enrichment data is available to confirm."}, status=400)
    if enrichment.status == "failed":
        return Response({"error": "Failed enrichment cannot be confirmed until a match is resolved."}, status=409)

    updates = request.data or {}
    for field_name in [
        "normalized_address", "address_line_1", "city", "state", "postal_code", "country",
        "county", "jurisdiction", "parcel_id", "apn", "property_type",
    ]:
        if field_name in updates:
            setattr(enrichment, field_name, (updates.get(field_name) or "").strip())
    for field_name in ["latitude", "longitude", "lot_size", "building_area", "assessed_value", "tax_value"]:
        if field_name in updates:
            setattr(enrichment, field_name, updates.get(field_name) or None)
    if "year_built" in updates:
        enrichment.year_built = updates.get("year_built") or None

    if enrichment.normalized_address:
        prop.address = enrichment.normalized_address
    if enrichment.latitude is not None:
        prop.latitude = enrichment.latitude
    if enrichment.longitude is not None:
        prop.longitude = enrichment.longitude
    if enrichment.building_area is not None and not prop.size_sqm:
        prop.size_sqm = float(enrichment.building_area)
    if enrichment.assessed_value is not None and not prop.estimated_value:
        prop.estimated_value = enrichment.assessed_value
    if not prop.title:
        prop.title = enrichment.normalized_address or prop.address or "Untitled property"
    prop.save()

    enrichment.status = "enriched"
    enrichment.confirmed_at = timezone.now()
    enrichment.confirmed_by = request.user
    enrichment.save()
    transition = sync_pre_tokenization_lifecycle(prop, user=request.user)
    notifications = [push_notification(request, "success", "Autofill reviewed and confirmed.")]
    if transition:
        notifications.append(push_notification(request, "success", transition.message))
    return Response({
        "property": property_payload(prop, request.user),
        "enrichment": enrichment_to_payload(enrichment),
        "notifications": notifications,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def property_readiness(request, pk):
    prop = _issuer_property_or_404(request.user, pk)
    return Response(evaluate_property_readiness(prop, user=request.user))


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
    if not can_upload_documents(prop):
        return Response({"error": "Documents cannot be uploaded in the current property state.", "code": "invalid_lifecycle_state"}, status=409)
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
        transition = sync_pre_tokenization_lifecycle(prop, user=request.user)
        notifications = [push_notification(request, "success", "Document uploaded successfully.")]
        if transition:
            notifications.append(push_notification(request, "success", transition.message))
        return Response({
            "document": document_payload(doc),
            "property": property_payload(prop, request.user),
            "notifications": notifications,
        }, status=201)
    except Exception:
        doc.processing_status = "failed"
        doc.save(update_fields=["processing_status"])
        return Response({
            "error": "Document processing could not be completed. Please try again or contact support.",
            "document": document_payload(doc),
        }, status=500)


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
    if active_subscription_required(request.user):
        return Response({"error": "An active issuer subscription is required for tokenization."}, status=403)
    if not can_attempt_tokenization(prop):
        return Response({"error": "Property cannot be tokenized in its current lifecycle state.", "code": "invalid_lifecycle_state"}, status=409)

    client = ZcashClient()
    readiness = evaluate_property_readiness(prop, user=request.user, zsa_report=client.configuration_report())
    if not readiness["ready_for_tokenization"]:
        notification = push_notification(request, "warning", "Property is not ready for tokenization.")
        return Response({
            "error": "Property is not ready for tokenization.",
            "code": "not_ready_for_tokenization",
            "readiness": readiness,
            "notifications": [notification],
        }, status=409)
    sync_pre_tokenization_lifecycle(prop, user=request.user, zsa_report=readiness["zsa"])
    prop.refresh_from_db()

    issuer_zaddr = request.data.get("issuer_zaddr", "").strip()
    if not issuer_zaddr:
        return Response({"error": "Issuer shielded address is required."}, status=400)

    asset_symbol = f"ZREAL-PROP-{prop.id}"
    metadata = _safe_tokenization_metadata(prop, asset_symbol)
    try:
        client.validate_issue_configuration(
            issuer_zaddr=issuer_zaddr,
            asset_symbol=asset_symbol,
            total_shares=prop.total_shares,
            metadata=metadata,
        )
    except (ZcashConfigurationError, ValueError, RuntimeError) as exc:
        notification = push_notification(request, "error", "Tokenization setup is incomplete.")
        return Response({
            "error": client.safe_error_message(exc),
            "code": "invalid_zsa_configuration",
            "property": property_payload(prop, request.user),
            "operation": None,
            "notifications": [notification],
        }, status=409)

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
        set_property_status(prop, "tokenization_pending")
        result = client.issue_zsa(
            issuer_zaddr=issuer_zaddr,
            asset_symbol=operation.asset_symbol,
            total_shares=prop.total_shares,
            metadata=metadata,
        )
        operation.mark_from_result(result)
        sync_property_from_operation(prop, operation)
        notification = push_notification(request, "success", "Tokenization submitted.")
        return Response({
            "operation": tokenization_operation_payload(operation, request.user),
            "property": property_payload(prop, request.user),
            "notifications": [notification],
        }, status=201)
    except (ZcashConfigurationError, ValueError, RuntimeError) as exc:
        operation.status = "failed"
        operation.error = client.safe_error_message(exc)
        operation.failed_at = timezone.now()
        operation.save()
        prop.tokenization_status = "failed"
        prop.tokenization_error = client.safe_error_message(exc)
        if prop.status == "tokenization_pending":
            prop.status = "ready_for_tokenization"
            prop.save(update_fields=["status", "tokenization_status", "tokenization_error", "updated_at"])
        else:
            prop.save(update_fields=["tokenization_status", "tokenization_error", "updated_at"])
        notification = push_notification(request, "error", "Tokenization failed.")
        return Response({
            "error": client.safe_error_message(exc),
            "operation": tokenization_operation_payload(operation, request.user),
            "property": property_payload(prop, request.user),
            "notifications": [notification],
        }, status=400)


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
    client = ZcashClient()
    try:
        result = client.refresh_zsa_status(operation.operation_id)
        operation.mark_from_result(result)
        sync_property_from_operation(operation.property, operation)
        notification = push_notification(request, "success", "Status refreshed.")
        return Response({"operation": tokenization_operation_payload(operation, request.user), "notifications": [notification]})
    except (ZcashConfigurationError, ValueError, RuntimeError) as exc:
        operation.status = "failed"
        operation.error = client.safe_error_message(exc)
        operation.failed_at = timezone.now()
        operation.save(update_fields=["status", "error", "failed_at", "updated_at"])
        sync_property_from_operation(operation.property, operation)
        notification = push_notification(request, "error", "Tokenization failed.")
        return Response({"operation": tokenization_operation_payload(operation, request.user), "notifications": [notification]}, status=400)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def activate_property(request, pk):
    prop = _issuer_property_or_404(request.user, pk)
    if prop.status != "tokenized" or not prop.zsa_asset_id:
        return Response({"error": "Only tokenized properties with a real asset ID can be activated.", "code": "not_activatable"}, status=409)
    set_property_status(prop, "active")
    notification = push_notification(request, "success", "Property activated.")
    return Response({"property": property_payload(prop, request.user), "notifications": [notification]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def suspend_property(request, pk):
    prop = _issuer_property_or_404(request.user, pk)
    if prop.status != "active":
        return Response({"error": "Only active properties can be suspended.", "code": "not_suspendable"}, status=409)
    set_property_status(prop, "suspended")
    notification = push_notification(request, "warning", "Property suspended.")
    return Response({"property": property_payload(prop, request.user), "notifications": [notification]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def archive_property(request, pk):
    prop = _issuer_property_or_404(request.user, pk)
    set_property_status(prop, "archived")
    notification = push_notification(request, "warning", "Property archived.")
    return Response({"property": property_payload(prop, request.user), "notifications": [notification]})
