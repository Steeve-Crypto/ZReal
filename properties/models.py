import builtins

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from .lifecycle import PROPERTY_STATUSES

class Property(models.Model):
    """
    Core Real Estate Property model with geospatial support.
    Ready for ZSA tokenization linking.
    """
    STATUS_CHOICES = list(PROPERTY_STATUSES)
    TOKENIZATION_STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('pending', 'Pending'),
        ('broadcast', 'Broadcast'),
        ('confirmed', 'Confirmed'),
        ('failed', 'Failed'),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_properties')
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=500)
    
    # Map coordinates. Ordinary fields keep local development free of GDAL/PostGIS.
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    plot_geojson = models.JSONField(default=dict, blank=True, help_text="Optional plot boundary GeoJSON")
    
    size_sqm = models.FloatField(null=True, blank=True, help_text="Total size in square meters")
    bedrooms = models.PositiveIntegerField(null=True, blank=True)
    bathrooms = models.PositiveIntegerField(null=True, blank=True)
    estimated_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Tokenization fields
    total_shares = models.PositiveIntegerField(default=10000, help_text="Total fractional shares / ZSA tokens")
    zsa_asset_id = models.CharField(max_length=100, blank=True, null=True, 
                                    help_text="Zcash Shielded Asset identifier once issued")
    zcash_operation_id = models.CharField(max_length=128, blank=True, null=True)
    zcash_txid = models.CharField(max_length=128, blank=True, null=True)
    tokenization_status = models.CharField(
        max_length=20,
        choices=TOKENIZATION_STATUS_CHOICES,
        default='not_started',
    )
    tokenization_error = models.TextField(blank=True)
    tokenized_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='draft')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.address})"

    class Meta:
        ordering = ['-created_at']


class PropertyEnrichment(models.Model):
    """Reviewable provider-derived property data, kept separate until confirmed."""

    STATUS_CHOICES = [
        ("not_started", "Not Started"),
        ("pending", "Pending"),
        ("enriched", "Enriched"),
        ("needs_review", "Needs Review"),
        ("failed", "Failed"),
    ]

    property = models.OneToOneField(Property, on_delete=models.CASCADE, related_name="enrichment")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="not_started")
    provider = models.CharField(max_length=64, blank=True)
    data_source = models.CharField(max_length=128, blank=True)
    source_record_id = models.CharField(max_length=255, blank=True)

    normalized_address = models.CharField(max_length=500, blank=True)
    address_line_1 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=128, blank=True)
    state = models.CharField(max_length=64, blank=True)
    postal_code = models.CharField(max_length=32, blank=True)
    country = models.CharField(max_length=64, blank=True, default="US")
    county = models.CharField(max_length=128, blank=True)
    jurisdiction = models.CharField(max_length=128, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    parcel_id = models.CharField(max_length=128, blank=True)
    apn = models.CharField(max_length=128, blank=True)
    lot_size = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    building_area = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    year_built = models.PositiveIntegerField(null=True, blank=True)
    property_type = models.CharField(max_length=128, blank=True)
    assessed_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    tax_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    match_confidence = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    blockers = models.JSONField(default=list, blank=True)
    candidates = models.JSONField(default=list, blank=True)
    safe_payload = models.JSONField(default=dict, blank=True)
    retrieved_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="confirmed_property_enrichments")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    @builtins.property
    def is_confirmed(self):
        return bool(self.confirmed_at)


class TokenizationOperation(models.Model):
    """Auditable record of an attempted real ZSA issuance."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('broadcast', 'Broadcast'),
        ('confirmed', 'Confirmed'),
        ('failed', 'Failed'),
    ]

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='tokenization_operations')
    issuer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tokenization_operations')
    issuer_zaddr = models.CharField(max_length=256)
    asset_symbol = models.CharField(max_length=64)
    total_shares = models.PositiveIntegerField()
    backend = models.CharField(max_length=64)
    metadata = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    operation_id = models.CharField(max_length=128, blank=True)
    txid = models.CharField(max_length=128, blank=True)
    asset_id = models.CharField(max_length=128, blank=True)
    error = models.TextField(blank=True)
    response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    broadcast_at = models.DateTimeField(null=True, blank=True)
    last_status_refreshed_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def mark_from_result(self, result):
        status = result.get('status') or 'pending'
        valid_statuses = {choice[0] for choice in self.STATUS_CHOICES}
        if status not in valid_statuses:
            raise ValueError(f"Unsupported tokenization status returned by backend: {status}")
        self.status = status
        self.operation_id = result.get('operation_id') or self.operation_id
        self.txid = result.get('txid') or self.txid
        self.asset_id = result.get('asset_id') or self.asset_id
        self.error = result.get('error') or ''
        self.response = result
        self.last_status_refreshed_at = timezone.now()
        if status == 'broadcast' and not self.broadcast_at:
            self.broadcast_at = timezone.now()
        if status == 'confirmed' and not self.confirmed_at:
            self.confirmed_at = timezone.now()
        if status == 'failed' and not self.failed_at:
            self.failed_at = timezone.now()
        self.save()

class PropertyInvestment(models.Model):
    """Tracks investor positions in tokenized properties."""
    investor = models.ForeignKey(User, on_delete=models.CASCADE)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='investments')
    shares_owned = models.PositiveIntegerField()
    purchase_tx_hash = models.CharField(max_length=100, blank=True, help_text="Zcash shielded tx hash")
    purchase_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('investor', 'property')


class PropertyDocument(models.Model):
    """
    Uploaded legal/property documents with AI-assisted extraction.
    Powers the 'Legal Shield' feature.
    """
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='documents')
    file = models.FileField(upload_to='property_documents/')
    document_type = models.CharField(max_length=100, blank=True, help_text="e.g. Deed, Title, Contract, Appraisal")
    
    # Extracted data
    extracted_text = models.TextField(blank=True)
    file_sha256 = models.CharField(max_length=64, blank=True)
    extracted_data = models.JSONField(default=dict, blank=True)  # Structured fields like address, size, etc.
    ocr_confidence = models.FloatField(null=True, blank=True)
    processing_status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ])
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Document for {self.property.title} ({self.document_type or 'Unknown'})"
