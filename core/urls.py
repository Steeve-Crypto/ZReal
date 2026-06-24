from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_redirect, name='dashboard_redirect'),
    path('issuer/dashboard/', views.issuer_dashboard, name='issuer_dashboard'),
    path('investor/portfolio/', views.investor_portfolio, name='investor_portfolio'),
]
