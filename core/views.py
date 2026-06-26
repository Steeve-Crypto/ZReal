from decimal import Decimal
import os
import tempfile

import stripe
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db import connection, connections
from django.db.migrations.executor import MigrationExecutor
from django.db.models import Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import RoleSelectionForm
from .models import UserProfile
from properties.lifecycle import PUBLIC_PROPERTY_STATUSES
from zcash_integration.zcash_client import ZcashClient


def _money_display(value):
    if value is None:
        return "No data yet"
    return f"${value:,.2f}"


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard_redirect')
    return redirect('property_map')


def health(request):
    return JsonResponse({"status": "ok"})


def _database_ok():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True, ""
    except Exception as exc:
        return False, str(exc)


def _migrations_applied():
    try:
        executor = MigrationExecutor(connections['default'])
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        return not plan, f"{len(plan)} unapplied migration(s)" if plan else ""
    except Exception as exc:
        return False, str(exc)


def _media_writable():
    try:
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=settings.MEDIA_ROOT, prefix="zreal-check-", delete=True):
            pass
        return True, ""
    except Exception as exc:
        return False, str(exc)


def _route_resolves(name):
    try:
        reverse(name)
        return True, ""
    except NoReverseMatch as exc:
        return False, str(exc)


@staff_member_required
def setup_status(request):
    """Internal local/admin setup checklist with secret-safe configuration status."""
    db_ok, db_detail = _database_ok()
    migrations_ok, migrations_detail = _migrations_applied()
    media_ok, media_detail = _media_writable()
    health_ok, health_detail = _route_resolves('health')
    zsa = ZcashClient().configuration_report()

    checks = [
        {'label': 'Database working', 'ok': db_ok, 'detail': db_detail},
        {'label': 'Migrations applied', 'ok': migrations_ok, 'detail': migrations_detail},
        {'label': 'Stripe configured', 'ok': bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_ISSUER_PRICE_ID), 'detail': 'STRIPE_SECRET_KEY and STRIPE_ISSUER_PRICE_ID'},
        {'label': 'ZSA tool path configured', 'ok': zsa['tool_path_configured'], 'detail': 'ZCASH_TX_TOOL_PATH'},
        {'label': 'ZSA issue command configured', 'ok': zsa['issue_command_configured'], 'detail': 'ZCASH_ZSA_ISSUE_COMMAND'},
        {'label': 'ZSA status command configured', 'ok': zsa['status_command_configured'], 'detail': 'ZCASH_ZSA_STATUS_COMMAND'},
        {'label': 'Zcash RPC URL configured', 'ok': zsa['rpc_url_configured'], 'detail': 'ZCASH_RPC_URL or ZCASHRPC_*'},
        {'label': 'Health endpoint route resolves', 'ok': health_ok, 'detail': health_detail or reverse('health')},
        {'label': 'Media/document upload path writable', 'ok': media_ok, 'detail': media_detail or str(settings.MEDIA_ROOT)},
    ]

    return render(request, 'core/setup_status.html', {
        'checks': checks,
        'zsa': zsa,
    })


@login_required
def dashboard_redirect(request):
    """Redirect users to the correct dashboard based on their role."""
    profile = request.user.profile

    if profile.is_issuer:
        return redirect('issuer_dashboard')
    if profile.is_investor:
        return redirect('investor_portfolio')
    return redirect('admin:index')


@login_required
def choose_role(request):
    form = RoleSelectionForm(request.POST or None, initial={'role': request.user.profile.role})
    if request.method == 'POST' and form.is_valid():
        request.user.profile.role = form.cleaned_data['role']
        request.user.profile.save()
        return redirect('dashboard_redirect')
    return render(request, 'core/choose_role.html', {'form': form})


@login_required
def issuer_dashboard(request):
    """Issuer Dashboard - manage real properties and tokenization attempts."""
    profile = request.user.profile

    if not profile.is_issuer:
        return redirect('dashboard_redirect')

    from properties.models import Property

    my_properties = Property.objects.filter(owner=request.user).prefetch_related(
        'tokenization_operations',
        'documents',
    )
    total_estimated_value = my_properties.aggregate(total=Sum('estimated_value'))['total']
    tokenized_count = my_properties.filter(status__in=PUBLIC_PROPERTY_STATUSES).count()
    zsa_issued_count = my_properties.exclude(zsa_asset_id__isnull=True).exclude(zsa_asset_id='').count()
    zsa_config = ZcashClient().configuration_report()

    context = {
        'profile': profile,
        'has_active_subscription': profile.has_active_subscription,
        'my_properties': my_properties,
        'can_issue_zsa': (
            profile.has_active_subscription
            if settings.REQUIRE_ACTIVE_SUBSCRIPTION_FOR_ZSA
            else True
        ),
        'property_count': my_properties.count(),
        'tokenized_count': tokenized_count,
        'total_estimated_value': total_estimated_value,
        'total_estimated_value_display': _money_display(total_estimated_value),
        'zsa_issued_count': zsa_issued_count,
        'zsa_backend': settings.ZSA_ISSUANCE_BACKEND,
        'zsa_tool_configured': bool(settings.ZCASH_TX_TOOL_PATH),
        'zsa_config': zsa_config,
    }
    return render(request, 'core/issuer_dashboard.html', context)


@login_required
def investor_portfolio(request):
    """Investor Portfolio - view real investment records only."""
    profile = request.user.profile

    if not profile.is_investor:
        return redirect('dashboard_redirect')

    from properties.models import Property, PropertyInvestment

    investments = PropertyInvestment.objects.filter(investor=request.user).select_related('property')
    holdings = []
    total_portfolio_value = Decimal('0')
    has_portfolio_value = False

    for investment in investments:
        prop = investment.property
        estimated_position_value = None
        ownership_percent = Decimal('0')

        if prop.total_shares:
            ownership_percent = (Decimal(investment.shares_owned) / Decimal(prop.total_shares)) * Decimal('100')

        if prop.estimated_value and prop.total_shares:
            estimated_position_value = (
                prop.estimated_value * Decimal(investment.shares_owned)
            ) / Decimal(prop.total_shares)
            total_portfolio_value += estimated_position_value
            has_portfolio_value = True

        holdings.append({
            'investment': investment,
            'property': prop,
            'shares_owned': investment.shares_owned,
            'ownership_percent': ownership_percent,
            'estimated_position_value': _money_display(estimated_position_value) if estimated_position_value is not None else None,
        })

    context = {
        'profile': profile,
        'investments': investments,
        'investment_count': investments.count(),
        'available_property_count': Property.objects.filter(status__in=PUBLIC_PROPERTY_STATUSES).count(),
        'holdings': holdings,
        'total_portfolio_value': total_portfolio_value,
        'total_portfolio_value_display': _money_display(total_portfolio_value) if has_portfolio_value else "No data yet",
    }
    return render(request, 'core/investor_portfolio.html', context)


@login_required
@require_POST
def create_checkout_session(request):
    """Create a Stripe Checkout Session for issuer subscription billing."""
    if not request.user.profile.is_issuer:
        return JsonResponse({"error": "Only issuers can subscribe"}, status=403)
    if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_ISSUER_PRICE_ID:
        return JsonResponse({
            "error": "Stripe is not configured. Set STRIPE_SECRET_KEY and STRIPE_ISSUER_PRICE_ID."
        }, status=400)

    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        checkout_session = stripe.checkout.Session.create(
            customer_email=request.user.email,
            payment_method_types=['card'],
            mode='subscription',
            line_items=[{
                'price': settings.STRIPE_ISSUER_PRICE_ID,
                'quantity': 1,
            }],
            success_url=request.build_absolute_uri('/billing/success/') + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.build_absolute_uri('/billing/cancel/'),
            metadata={
                'user_id': request.user.id,
                'plan': 'issuer_pro',
            },
        )
        return JsonResponse({'id': checkout_session.id, 'url': checkout_session.url})
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=400)


@csrf_exempt
def stripe_webhook(request):
    """Handle Stripe webhooks to update subscription status."""
    if not settings.DJSTRIPE_WEBHOOK_SECRET:
        return HttpResponse("Stripe webhook secret is not configured.", status=400)

    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.DJSTRIPE_WEBHOOK_SECRET)
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    if event['type'] == 'customer.subscription.created':
        subscription = event['data']['object']
        user_id = subscription.get('metadata', {}).get('user_id')
        if user_id:
            try:
                profile = UserProfile.objects.get(user_id=user_id)
                profile.subscription_status = 'active'
                profile.current_plan = subscription.get('metadata', {}).get('plan', 'issuer_pro')
                profile.stripe_customer_id = subscription.get('customer')
                profile.save()
            except UserProfile.DoesNotExist:
                pass

    elif event['type'] in ['customer.subscription.updated', 'customer.subscription.deleted']:
        subscription = event['data']['object']
        user_id = subscription.get('metadata', {}).get('user_id')
        if user_id:
            try:
                profile = UserProfile.objects.get(user_id=user_id)
                if event['type'] == 'customer.subscription.deleted':
                    profile.subscription_status = 'canceled'
                else:
                    profile.subscription_status = subscription.get('status', 'active')
                profile.save()
            except UserProfile.DoesNotExist:
                pass

    return HttpResponse(status=200)


def billing_success(request):
    return render(request, 'core/billing_success.html')


def billing_cancel(request):
    return render(request, 'core/billing_cancel.html')
