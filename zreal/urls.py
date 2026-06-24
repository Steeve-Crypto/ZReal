from django.contrib import admin
from django.urls import path, include
from properties.views import (
    property_map, 
    issue_zsa_example, 
    distribute_rental_income,
    generate_sapling_address_view,
    upload_property_document,
    premium_geospatial_map,
    property_timeline,
    export_legal_shield_report,
    health_check,
    falco_webhook
)
from django.urls import include
from rest_framework.routers import DefaultRouter
from properties.views import PropertyViewSet

router = DefaultRouter()
router.register(r'api/properties', PropertyViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('properties/map/', property_map, name='property_map'),
    path('properties/<int:pk>/issue-zsa/', issue_zsa_example, name='issue_zsa'),
    path('properties/<int:pk>/distribute/', distribute_rental_income, name='distribute_rental'),
    path('zcash/generate-sapling-address/', generate_sapling_address_view, name='generate_sapling_address'),
    path('', include(router.urls)),  # API
    path('accounts/', include('allauth.urls')),  # Auth
]
