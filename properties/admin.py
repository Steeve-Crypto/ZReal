from django.contrib import admin
from .models import Property, PropertyInvestment, PropertyDocument, ZSAConfig


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'status', 'zsa_asset_id', 'zsa_issuance_method', 'created_at')
    list_filter = ('status', 'zsa_issuance_method')
    search_fields = ('title', 'address', 'zsa_asset_id')


@admin.register(PropertyDocument)
class PropertyDocumentAdmin(admin.ModelAdmin):
    list_display = ('property', 'document_type', 'processing_status', 'uploaded_at')
    list_filter = ('processing_status', 'document_type')


@admin.register(ZSAConfig)
class ZSAConfigAdmin(admin.ModelAdmin):
    list_display = ('strategy', 'updated_at', 'notes')
    readonly_fields = ('updated_at',)

    def has_add_permission(self, request):
        # Only allow one config record
        return not ZSAConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
