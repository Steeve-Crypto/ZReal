from django.urls import path

from core import api as core_api
from properties import api as property_api


urlpatterns = [
    path("health/", core_api.api_health, name="api_health"),
    path("csrf/", core_api.csrf_token, name="api_csrf"),
    path("notifications/", core_api.notifications, name="api_notifications"),
    path("me/", core_api.current_user, name="api_current_user"),
    path("role/", core_api.role_status, name="api_role_status"),
    path("dashboard/issuer/", core_api.issuer_dashboard, name="api_issuer_dashboard"),
    path("dashboard/investor/", core_api.investor_dashboard, name="api_investor_dashboard"),
    path("setup/status/", core_api.setup_status, name="api_setup_status"),
    path("properties/", property_api.property_list, name="api_property_list"),
    path("properties/browse/", property_api.investor_browse, name="api_investor_browse"),
    path("properties/new/", property_api.create_property, name="api_property_create"),
    path("properties/<int:pk>/", property_api.property_detail, name="api_property_detail"),
    path("properties/<int:pk>/edit/", property_api.edit_property, name="api_property_edit"),
    path("properties/<int:pk>/readiness/", property_api.property_readiness, name="api_property_readiness"),
    path("properties/<int:pk>/documents/", property_api.property_documents, name="api_property_documents"),
    path("properties/<int:pk>/documents/upload/", property_api.upload_document, name="api_upload_document"),
    path("properties/<int:pk>/tokenize/", property_api.issue_property_tokenization, name="api_issue_tokenization"),
    path("properties/<int:pk>/activate/", property_api.activate_property, name="api_activate_property"),
    path("properties/<int:pk>/suspend/", property_api.suspend_property, name="api_suspend_property"),
    path("properties/<int:pk>/archive/", property_api.archive_property, name="api_archive_property"),
    path("zsa/config/", property_api.zsa_config_readiness, name="api_zsa_config"),
    path("tokenization/operations/<int:pk>/", property_api.tokenization_operation_detail, name="api_tokenization_operation"),
    path("tokenization/operations/<int:pk>/refresh/", property_api.refresh_tokenization_operation, name="api_refresh_tokenization_operation"),
]
