from decimal import Decimal

from rest_framework import serializers

from .models import Property
from .lifecycle import can_attempt_tokenization, can_edit_property, can_upload_documents, evaluate_property_readiness


SAFE_EXTRACTED_KEYS = ("detected_address", "detected_size", "ocr_used")


def masked_zaddr(address):
    if not address:
        return None
    if len(address) <= 16:
        return f"{address[:4]}..."
    return f"{address[:8]}...{address[-6:]}"


def safe_document_metadata(document):
    data = document.extracted_data or {}
    return {key: data[key] for key in SAFE_EXTRACTED_KEYS if key in data and data[key]}


def document_payload(document):
    return {
        "id": document.id,
        "document_type": document.document_type,
        "document_hash": document.file_sha256,
        "processing_status": document.processing_status,
        "safe_extracted_metadata": safe_document_metadata(document),
        "uploaded_at": document.uploaded_at.isoformat() if document.uploaded_at else None,
        "processed_at": document.processed_at.isoformat() if document.processed_at else None,
    }


def tokenization_operation_payload(operation, user):
    can_view_raw = bool(user and user.is_authenticated and user.is_staff)
    payload = {
        "id": operation.id,
        "property": {
            "id": operation.property_id,
            "title": operation.property.title,
        },
        "status": operation.status,
        "backend": operation.backend,
        "method": operation.backend,
        "asset_symbol": operation.asset_symbol,
        "total_shares": operation.total_shares,
        "issuer_zaddr_masked": masked_zaddr(operation.issuer_zaddr),
        "operation_id": operation.operation_id or None,
        "txid": operation.txid or None,
        "asset_id": operation.asset_id or None,
        "safe_metadata": operation.metadata or {},
        "error": operation.error or None,
        "created_at": operation.created_at.isoformat() if operation.created_at else None,
        "updated_at": operation.updated_at.isoformat() if operation.updated_at else None,
        "broadcast_at": operation.broadcast_at.isoformat() if operation.broadcast_at else None,
        "confirmed_at": operation.confirmed_at.isoformat() if operation.confirmed_at else None,
        "failed_at": operation.failed_at.isoformat() if operation.failed_at else None,
        "last_status_refreshed_at": operation.last_status_refreshed_at.isoformat() if operation.last_status_refreshed_at else None,
        "can_refresh": bool(operation.operation_id and operation.status in ["pending", "broadcast", "failed"]),
        "can_view_raw_response": can_view_raw,
    }
    if can_view_raw:
        payload["raw_response"] = operation.response or {}
    return payload


def _latest_operation_payload(prop, user):
    operation = prop.tokenization_operations.first()
    return tokenization_operation_payload(operation, user) if operation else None


def property_payload(prop, user=None, zsa_report=None):
    is_owner = bool(user and user.is_authenticated and prop.owner_id == user.id)
    readiness = evaluate_property_readiness(prop, user=user, zsa_report=zsa_report)
    return {
        "id": prop.id,
        "title": prop.title,
        "description": prop.description,
        "address": prop.address,
        "latitude": str(prop.latitude) if prop.latitude is not None else None,
        "longitude": str(prop.longitude) if prop.longitude is not None else None,
        "size_sqm": prop.size_sqm,
        "bedrooms": prop.bedrooms,
        "bathrooms": prop.bathrooms,
        "estimated_value": str(prop.estimated_value) if prop.estimated_value is not None else None,
        "total_shares": prop.total_shares,
        "status": prop.status,
        "status_display": prop.get_status_display(),
        "lifecycle": {
            "status": prop.status,
            "status_display": prop.get_status_display(),
            "next_action": readiness["next_action"],
        },
        "readiness": readiness,
        "tokenization": {
            "status": prop.tokenization_status,
            "status_display": prop.get_tokenization_status_display(),
            "operation_id": prop.zcash_operation_id,
            "txid": prop.zcash_txid,
            "asset_id": prop.zsa_asset_id,
            "error": prop.tokenization_error or None,
            "tokenized_at": prop.tokenized_at.isoformat() if prop.tokenized_at else None,
        },
        "latest_tokenization_operation": _latest_operation_payload(prop, user),
        "document_count": prop.documents.count() if hasattr(prop, "documents") else 0,
        "created_at": prop.created_at.isoformat() if prop.created_at else None,
        "updated_at": prop.updated_at.isoformat() if prop.updated_at else None,
        "ownership": {
            "is_owner": is_owner,
            "can_edit": is_owner and can_edit_property(prop),
            "can_upload_documents": is_owner and can_upload_documents(prop),
            "can_tokenize": is_owner and can_attempt_tokenization(prop),
        },
    }


def dashboard_property_payload(prop, user, zsa_report=None):
    payload = property_payload(prop, user, zsa_report=zsa_report)
    payload["documents"] = [document_payload(doc) for doc in prop.documents.all()]
    payload["tokenization_operations"] = [
        tokenization_operation_payload(operation, user)
        for operation in prop.tokenization_operations.all()
    ]
    return payload


def investment_payload(investment):
    prop = investment.property
    ownership_percent = Decimal("0")
    estimated_position_value = None
    if prop.total_shares:
        ownership_percent = (Decimal(investment.shares_owned) / Decimal(prop.total_shares)) * Decimal("100")
    if prop.estimated_value and prop.total_shares:
        estimated_position_value = (prop.estimated_value * Decimal(investment.shares_owned)) / Decimal(prop.total_shares)
    return {
        "id": investment.id,
        "property": property_payload(prop, investment.investor),
        "shares_owned": investment.shares_owned,
        "ownership_percent": str(ownership_percent),
        "estimated_position_value": str(estimated_position_value) if estimated_position_value is not None else None,
        "purchase_date": investment.purchase_date.isoformat() if investment.purchase_date else None,
        "purchase_tx_hash": investment.purchase_tx_hash or None,
    }

class PropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = '__all__'
        read_only_fields = (
            'owner',
            'zsa_asset_id',
            'zcash_operation_id',
            'zcash_txid',
            'tokenization_status',
            'tokenization_error',
            'tokenized_at',
            'status',
            'created_at',
        )
