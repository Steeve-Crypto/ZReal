from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from properties.views import (
    property_map, 
    issue_zsa_example, 
    generate_sapling_address_view,
    property_create,
    property_edit,
    investor_property_browse,
    refresh_zsa_status,
    upload_property_document,
    tokenization_operation_detail,
    refresh_tokenization_operation,
    validate_zsa_configuration,
)
from rest_framework.routers import DefaultRouter
from properties.views import PropertyViewSet

router = DefaultRouter()
router.register(r'api/properties', PropertyViewSet, basename='property')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('properties/map/', property_map, name='property_map'),
    path('properties/browse/', investor_property_browse, name='investor_property_browse'),
    path('investor/browse/', investor_property_browse, name='investor_browse'),
    path('properties/new/', property_create, name='property_create'),
    path('properties/<int:pk>/edit/', property_edit, name='property_edit'),
    path('properties/<int:pk>/issue-zsa/', issue_zsa_example, name='issue_zsa'),
    path('properties/<int:pk>/refresh-zsa-status/', refresh_zsa_status, name='refresh_zsa_status'),
    path('properties/<int:pk>/upload-document/', upload_property_document, name='upload_property_document'),
    path('tokenization/operations/<int:pk>/', tokenization_operation_detail, name='tokenization_operation_detail'),
    path('tokenization/operations/<int:pk>/refresh/', refresh_tokenization_operation, name='refresh_tokenization_operation'),
    path('zsa/config/validate/', validate_zsa_configuration, name='zsa_config_validate'),
    path('zcash/zsa-config/validate/', validate_zsa_configuration, name='validate_zsa_configuration'),
    path('zcash/generate-sapling-address/', generate_sapling_address_view, name='generate_sapling_address'),
    path('', include('core.urls')),
    path('', include(router.urls)),  # API
    path('accounts/', include('allauth.urls')),  # Auth
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
