from django.contrib import admin
from .models import Property, PropertyInvestment, PropertyDocument, TokenizationOperation


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'status', 'tokenization_status', 'zsa_asset_id', 'created_at')
    list_filter = ('status', 'tokenization_status')
    search_fields = ('title', 'address', 'zsa_asset_id')


@admin.register(PropertyInvestment)
class PropertyInvestmentAdmin(admin.ModelAdmin):
    list_display = ('investor', 'property', 'shares_owned', 'purchase_date')
    search_fields = ('investor__username', 'property__title', 'purchase_tx_hash')


@admin.register(PropertyDocument)
class PropertyDocumentAdmin(admin.ModelAdmin):
    list_display = ('property', 'document_type', 'processing_status', 'file_sha256', 'uploaded_at')
    list_filter = ('processing_status', 'document_type')


@admin.register(TokenizationOperation)
class TokenizationOperationAdmin(admin.ModelAdmin):
    list_display = ('property', 'issuer', 'backend', 'status', 'operation_id', 'txid', 'asset_id', 'created_at')
    list_filter = ('backend', 'status')
    search_fields = ('property__title', 'issuer__username', 'operation_id', 'txid', 'asset_id')
    readonly_fields = (
        'created_at',
        'updated_at',
        'broadcast_at',
        'last_status_refreshed_at',
        'confirmed_at',
        'failed_at',
        'metadata',
        'response',
    )
