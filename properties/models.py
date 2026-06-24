from django.contrib.gis.db import models as gis_models
from django.contrib.auth.models import User
from django.db import models

class Property(models.Model):
    """
    Core Real Estate Property model with geospatial support.
    Ready for ZSA tokenization linking.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('tokenizing', 'Tokenizing'),
        ('tokenized', 'Tokenized (ZSA Issued)'),
        ('active', 'Active - Open for Investment'),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_properties')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=500)
    
    # Geospatial fields (PostGIS)
    location = gis_models.PointField(geography=True, help_text="Lat/Long of property")
    plot_polygon = gis_models.PolygonField(geography=True, null=True, blank=True, 
                                           help_text="Exact plot boundaries for layouts")
    
    size_sqm = models.FloatField(help_text="Total size in square meters")
    bedrooms = models.PositiveIntegerField(null=True, blank=True)
    bathrooms = models.PositiveIntegerField(null=True, blank=True)
    estimated_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Tokenization fields
    total_shares = models.PositiveIntegerField(default=10000, help_text="Total fractional shares / ZSA tokens")
    zsa_asset_id = models.CharField(max_length=100, blank=True, null=True, 
                                    help_text="Zcash Shielded Asset identifier once issued")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.address})"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            gis_models.Index(fields=['location']),
        ]

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
