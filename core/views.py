from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import UserProfile

@login_required
def dashboard_redirect(request):
    """Redirect users to the correct dashboard based on their role."""
    profile = request.user.profile
    
    if profile.is_issuer:
        return redirect('issuer_dashboard')
    elif profile.is_investor:
        return redirect('investor_portfolio')
    else:
        return redirect('admin:index')  # or a default page


@login_required
def issuer_dashboard(request):
    """Issuer Dashboard - Manage properties, issue ZSA, billing."""
    profile = request.user.profile
    
    if not profile.is_issuer:
        return redirect('dashboard_redirect')
    
    # Check subscription status
    has_active_sub = profile.has_active_subscription
    
    from properties.models import Property
    my_properties = Property.objects.filter(owner=request.user)
    
    context = {
        'profile': profile,
        'has_active_subscription': has_active_sub,
        'my_properties': my_properties,
        'can_issue_zsa': has_active_sub,  # Gate ZSA issuance behind subscription
    }
    return render(request, 'core/issuer_dashboard.html', context)


@login_required
def investor_portfolio(request):
    """Investor Portfolio - View investments and private balances."""
    profile = request.user.profile
    
    if not profile.is_investor:
        return redirect('dashboard_redirect')
    
    from properties.models import PropertyInvestment
    investments = PropertyInvestment.objects.filter(investor=request.user).select_related('property')
    
    context = {
        'profile': profile,
        'investments': investments,
        'viewing_key_available': bool(profile.default_viewing_key),
    }
    return render(request, 'core/investor_portfolio.html', context)


# ==================== STRIPE SUBSCRIPTION BILLING ====================

@login_required
def create_checkout_session(request):
    """Create a Stripe Checkout Session for Issuer subscription."""
    if not request.user.profile.is_issuer:
        return JsonResponse({"error": "Only issuers can subscribe"}, status=403)

    try:
        checkout_session = stripe.checkout.Session.create(
            customer_email=request.user.email,
            payment_method_types=['card'],
            mode='subscription',
            line_items=[{
                'price': 'price_issuer_pro_monthly',  # ← Replace with your real Stripe Price ID
                'quantity': 1,
            }],
            success_url=request.build_absolute_uri('/billing/success/') + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.build_absolute_uri('/billing/cancel/'),
            metadata={
                'user_id': request.user.id,
                'plan': 'issuer_pro'
            }
        )
        return JsonResponse({'id': checkout_session.id, 'url': checkout_session.url})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
def stripe_webhook(request):
    """Handle Stripe webhooks to update subscription status."""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.DJSTRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    # Handle subscription events
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
