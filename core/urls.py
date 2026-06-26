from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('health', views.health, name='health_slashless'),
    path('health/', views.health, name='health'),
    path('setup/', views.setup_status, name='setup'),
    path('setup/status/', views.setup_status, name='setup_status'),
    path('dashboard/', views.dashboard_redirect, name='dashboard_redirect'),
    path('profile/role/', views.choose_role, name='choose_role'),
    path('issuer/dashboard/', views.issuer_dashboard, name='issuer_dashboard'),
    path('investor/portfolio/', views.investor_portfolio, name='investor_portfolio'),
    path('billing/create-checkout-session/', views.create_checkout_session, name='create_checkout_session'),
    path('billing/success/', views.billing_success, name='billing_success'),
    path('billing/cancel/', views.billing_cancel, name='billing_cancel'),
    path('billing/stripe-webhook/', views.stripe_webhook, name='stripe_webhook'),
]
