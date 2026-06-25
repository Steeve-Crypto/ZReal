from decimal import Decimal
import os
import tempfile

from django.conf import settings
from django.db import connection, connections
from django.db.migrations.executor import MigrationExecutor
from django.db.models import Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from properties.models import Property, PropertyInvestment
from properties.serializers import dashboard_property_payload, investment_payload
from zcash_integration.zcash_client import ZcashClient


def money_value(value):
    return str(value) if value is not None else None


@api_view(["GET"])
@permission_classes([AllowAny])
def api_health(request):
    return Response({"status": "ok"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def current_user(request):
    profile = request.user.profile
    return Response({
        "id": request.user.id,
        "username": request.user.username,
        "email": request.user.email,
        "is_staff": request.user.is_staff,
        "profile": {
            "role": profile.role,
            "is_issuer": profile.is_issuer,
            "is_investor": profile.is_investor,
            "subscription_status": profile.subscription_status,
            "current_plan": profile.current_plan,
            "has_active_subscription": profile.has_active_subscription,
        },
    })


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def role_status(request):
    profile = request.user.profile
    if request.method == "PATCH":
        role = request.data.get("role")
        valid_roles = {choice[0] for choice in profile.ROLE_CHOICES}
        if role not in valid_roles:
            return Response({"error": "Invalid role."}, status=400)
        profile.role = role
        profile.save(update_fields=["role", "updated_at"])

    return Response({
        "role": profile.role,
        "is_issuer": profile.is_issuer,
        "is_investor": profile.is_investor,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def issuer_dashboard(request):
    profile = request.user.profile
    if not profile.is_issuer:
        return Response({"error": "Issuer role required."}, status=403)

    properties = Property.objects.filter(owner=request.user).prefetch_related("documents", "tokenization_operations")
    total_estimated_value = properties.aggregate(total=Sum("estimated_value"))["total"]
    zsa_config = ZcashClient().configuration_report()

    return Response({
        "metrics": {
            "property_count": properties.count(),
            "tokenized_count": properties.filter(status__in=["tokenized", "active"]).count(),
            "total_estimated_value": money_value(total_estimated_value),
            "zsa_issued_count": properties.exclude(zsa_asset_id__isnull=True).exclude(zsa_asset_id="").count(),
        },
        "zsa_config": zsa_config,
        "properties": [dashboard_property_payload(prop, request.user) for prop in properties],
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def investor_dashboard(request):
    profile = request.user.profile
    if not profile.is_investor:
        return Response({"error": "Investor role required."}, status=403)

    investments = PropertyInvestment.objects.filter(investor=request.user).select_related("property")
    holdings = []
    total_portfolio_value = Decimal("0")
    has_portfolio_value = False

    for investment in investments:
        payload = investment_payload(investment)
        if payload["estimated_position_value"] is not None:
            total_portfolio_value += Decimal(payload["estimated_position_value"])
            has_portfolio_value = True
        holdings.append(payload)

    return Response({
        "metrics": {
            "investment_count": investments.count(),
            "available_property_count": Property.objects.filter(status__in=["tokenized", "active"]).count(),
            "total_portfolio_value": str(total_portfolio_value) if has_portfolio_value else None,
        },
        "holdings": holdings,
    })


def _database_ok():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True
    except Exception:
        return False


def _migrations_applied():
    try:
        executor = MigrationExecutor(connections["default"])
        return not executor.migration_plan(executor.loader.graph.leaf_nodes())
    except Exception:
        return False


def _media_writable():
    try:
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=settings.MEDIA_ROOT, prefix="zreal-check-", delete=True):
            pass
        return True
    except Exception:
        return False


@api_view(["GET"])
@permission_classes([IsAdminUser])
def setup_status(request):
    zsa = ZcashClient().configuration_report()
    return Response({
        "database_working": _database_ok(),
        "migrations_applied": _migrations_applied(),
        "stripe_configured": bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_ISSUER_PRICE_ID),
        "zsa_ready": zsa["ready"],
        "zsa_configured": zsa["configured"],
        "media_writable": _media_writable(),
        "zsa": zsa,
    })
