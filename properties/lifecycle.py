from dataclasses import dataclass
from typing import Any

from django.conf import settings

from zcash_integration.zcash_client import ZcashClient


PROPERTY_STATUSES = (
    ("draft", "Draft"),
    ("documents_uploaded", "Documents Uploaded"),
    ("ready_for_review", "Ready for Review"),
    ("ready_for_tokenization", "Ready for Tokenization"),
    ("tokenization_pending", "Tokenization Pending"),
    ("tokenized", "Tokenized"),
    ("active", "Active"),
    ("suspended", "Suspended"),
    ("archived", "Archived"),
)

PUBLIC_PROPERTY_STATUSES = ("tokenized", "active")
EDIT_BLOCKED_STATUSES = ("archived", "suspended", "tokenization_pending", "tokenized", "active")
TOKENIZATION_BLOCKED_STATUSES = ("tokenization_pending", "tokenized", "active", "suspended", "archived")

VALID_TRANSITIONS = {
    "draft": {"documents_uploaded", "ready_for_review", "ready_for_tokenization", "archived"},
    "documents_uploaded": {"ready_for_review", "ready_for_tokenization", "archived"},
    "ready_for_review": {"ready_for_tokenization", "archived"},
    "ready_for_tokenization": {"tokenization_pending", "archived"},
    "tokenization_pending": {"tokenized", "ready_for_tokenization", "archived"},
    "tokenized": {"active", "suspended", "archived"},
    "active": {"suspended", "archived"},
    "suspended": {"active", "archived"},
    "archived": set(),
}


@dataclass(frozen=True)
class LifecycleTransition:
    status: str
    message: str


class InvalidLifecycleTransition(ValueError):
    pass


def completed_documents(prop):
    return prop.documents.filter(processing_status="completed").exclude(file_sha256="").order_by("-processed_at")


def property_has_required_documents(prop):
    return completed_documents(prop).exists()


def _check(key: str, label: str, ok: bool, detail: str = "", required: bool = True) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "ok": bool(ok),
        "required": required,
        "detail": detail,
    }


def _enrichment_summary(enrichment, requires_review: bool) -> dict[str, Any]:
    if not enrichment:
        return {
            "status": "not_started",
            "is_confirmed": False,
            "trusted_for_readiness": True,
            "normalized_address": None,
            "match_confidence": None,
            "warnings": [],
            "blockers": [],
        }
    return {
        "status": enrichment.status,
        "is_confirmed": bool(enrichment.confirmed_at),
        "trusted_for_readiness": not requires_review,
        "normalized_address": enrichment.normalized_address or None,
        "match_confidence": str(enrichment.match_confidence) if enrichment.match_confidence is not None else None,
        "warnings": enrichment.warnings or [],
        "blockers": enrichment.blockers or [],
    }


def evaluate_property_readiness(prop, user=None, zsa_report=None):
    if zsa_report is None:
        zsa_report = ZcashClient().configuration_report()

    profile = getattr(prop.owner, "profile", None)
    requester_profile = getattr(user, "profile", None) if user and user.is_authenticated else None
    is_owner = bool(user and user.is_authenticated and prop.owner_id == user.id)
    has_documents = property_has_required_documents(prop)
    has_estimated_value = bool(prop.estimated_value and prop.estimated_value > 0)
    has_valid_shares = bool(prop.total_shares and prop.total_shares > 0)
    enrichment = getattr(prop, "enrichment", None)
    enrichment_requires_review = bool(
        enrichment
        and enrichment.status in ("pending", "enriched", "needs_review")
        and not enrichment.confirmed_at
    )
    issuer_role_valid = bool(profile and profile.is_issuer)
    requester_can_issue = bool(is_owner and requester_profile and requester_profile.is_issuer)
    zsa_ready = bool(zsa_report.get("ready"))

    checks = [
        _check("required_documents_present", "Required documents present", has_documents, "At least one completed document with a SHA-256 hash is required."),
        _check("estimated_value_present", "Estimated value present", has_estimated_value, "Estimated value must be greater than zero."),
        _check("share_count_valid", "Share count valid", has_valid_shares, "Total shares must be greater than zero."),
        _check(
            "property_data_reviewed",
            "Property data reviewed",
            not enrichment_requires_review,
            "Autofilled property data must be reviewed and confirmed before tokenization.",
        ),
        _check("issuer_role_valid", "Issuer role valid", issuer_role_valid, "The property owner must have the issuer role."),
        _check("ownership_valid", "Ownership valid", requester_can_issue, "Only the issuer owner can tokenize this property."),
        _check("zsa_backend_configured", "Tokenization setup complete", zsa_ready, "Tokenization setup is incomplete. Contact an administrator or complete setup before issuance."),
    ]

    lifecycle_blockers = []
    if prop.status == "archived":
        lifecycle_blockers.append("Archived properties cannot be tokenized.")
    if prop.status == "suspended":
        lifecycle_blockers.append("Suspended properties cannot issue additional tokenizations.")
    if prop.status in ("tokenization_pending",):
        lifecycle_blockers.append("A tokenization operation is already pending.")
    if prop.status in ("tokenized", "active"):
        lifecycle_blockers.append("This property has already been tokenized.")

    blocking_issues = [check["detail"] for check in checks if check["required"] and not check["ok"]]
    blocking_issues.extend(lifecycle_blockers)
    ready_for_tokenization = not blocking_issues

    if prop.status == "archived":
        next_action = "none"
    elif prop.status == "suspended":
        next_action = "restore_or_archive"
    elif prop.status == "tokenization_pending":
        next_action = "refresh_tokenization_status"
    elif prop.status == "tokenized":
        next_action = "activate_property"
    elif prop.status == "active":
        next_action = "monitor_property"
    elif ready_for_tokenization:
        next_action = "issue_tokenization"
    elif not has_documents:
        next_action = "upload_documents"
    elif enrichment_requires_review:
        next_action = "review_property_enrichment"
    elif not has_estimated_value or not has_valid_shares:
        next_action = "complete_property_details"
    elif not zsa_ready:
        next_action = "configure_zsa_backend"
    else:
        next_action = "resolve_blocking_issues"

    return {
        "ready_for_tokenization": ready_for_tokenization,
        "checks": checks,
        "blocking_issues": blocking_issues,
        "enrichment": _enrichment_summary(enrichment, enrichment_requires_review),
        "zsa": zsa_report,
        "next_action": next_action,
    }


def ensure_transition(prop, target_status):
    if prop.status == target_status:
        return
    valid_targets = VALID_TRANSITIONS.get(prop.status, set())
    if target_status not in valid_targets:
        raise InvalidLifecycleTransition(f"Cannot move property from {prop.status} to {target_status}.")


def set_property_status(prop, target_status, update_fields=None):
    ensure_transition(prop, target_status)
    prop.status = target_status
    if update_fields is None:
        prop.save(update_fields=["status", "updated_at"])
    else:
        prop.save(update_fields=update_fields)


def sync_pre_tokenization_lifecycle(prop, user=None, zsa_report=None):
    if prop.status in ("tokenization_pending", "tokenized", "active", "suspended", "archived"):
        return None

    readiness = evaluate_property_readiness(prop, user=user, zsa_report=zsa_report)
    has_documents = next(check for check in readiness["checks"] if check["key"] == "required_documents_present")["ok"]
    has_value = next(check for check in readiness["checks"] if check["key"] == "estimated_value_present")["ok"]
    has_shares = next(check for check in readiness["checks"] if check["key"] == "share_count_valid")["ok"]

    target = prop.status
    message = ""
    if readiness["ready_for_tokenization"]:
        target = "ready_for_tokenization"
        message = "Property now ready for tokenization."
    elif has_documents and has_value and has_shares:
        target = "ready_for_review"
        message = "Property now ready for review."
    elif has_documents:
        target = "documents_uploaded"
        message = "Property documents uploaded."

    if target != prop.status:
        set_property_status(prop, target)
        return LifecycleTransition(status=target, message=message)
    return None


def sync_property_from_operation(prop, operation):
    prop.tokenization_status = operation.status
    prop.zcash_operation_id = operation.operation_id or prop.zcash_operation_id
    prop.zcash_txid = operation.txid or prop.zcash_txid
    prop.zsa_asset_id = operation.asset_id or prop.zsa_asset_id
    prop.tokenization_error = operation.error
    if operation.status in ["pending", "broadcast"]:
        ensure_transition(prop, "tokenization_pending")
        prop.status = "tokenization_pending"
    elif operation.status == "confirmed":
        ensure_transition(prop, "tokenized")
        prop.status = "tokenized"
        prop.tokenized_at = operation.confirmed_at or operation.updated_at
    elif operation.status == "failed":
        if prop.status == "tokenization_pending":
            prop.status = "ready_for_tokenization"
    prop.save()


def can_edit_property(prop):
    return prop.status not in EDIT_BLOCKED_STATUSES


def can_enrich_property(prop):
    return can_edit_property(prop)


def can_upload_documents(prop):
    return prop.status not in ("archived", "tokenization_pending", "tokenized", "active", "suspended")


def can_attempt_tokenization(prop):
    return prop.status not in TOKENIZATION_BLOCKED_STATUSES


def active_subscription_required(user):
    return settings.REQUIRE_ACTIVE_SUBSCRIPTION_FOR_ZSA and not user.profile.has_active_subscription
