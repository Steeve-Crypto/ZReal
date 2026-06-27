from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("properties", "0004_alter_property_status"),
    ]

    operations = [
        migrations.AlterField(
            model_name="property",
            name="title",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="property",
            name="size_sqm",
            field=models.FloatField(blank=True, help_text="Total size in square meters", null=True),
        ),
        migrations.CreateModel(
            name="PropertyEnrichment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("not_started", "Not Started"), ("pending", "Pending"), ("enriched", "Enriched"), ("needs_review", "Needs Review"), ("failed", "Failed")], default="not_started", max_length=20)),
                ("provider", models.CharField(blank=True, max_length=64)),
                ("data_source", models.CharField(blank=True, max_length=128)),
                ("source_record_id", models.CharField(blank=True, max_length=255)),
                ("normalized_address", models.CharField(blank=True, max_length=500)),
                ("address_line_1", models.CharField(blank=True, max_length=255)),
                ("city", models.CharField(blank=True, max_length=128)),
                ("state", models.CharField(blank=True, max_length=64)),
                ("postal_code", models.CharField(blank=True, max_length=32)),
                ("country", models.CharField(blank=True, default="US", max_length=64)),
                ("county", models.CharField(blank=True, max_length=128)),
                ("jurisdiction", models.CharField(blank=True, max_length=128)),
                ("latitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("longitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("parcel_id", models.CharField(blank=True, max_length=128)),
                ("apn", models.CharField(blank=True, max_length=128)),
                ("lot_size", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ("building_area", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ("year_built", models.PositiveIntegerField(blank=True, null=True)),
                ("property_type", models.CharField(blank=True, max_length=128)),
                ("assessed_value", models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True)),
                ("tax_value", models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True)),
                ("match_confidence", models.DecimalField(blank=True, decimal_places=4, max_digits=5, null=True)),
                ("warnings", models.JSONField(blank=True, default=list)),
                ("blockers", models.JSONField(blank=True, default=list)),
                ("candidates", models.JSONField(blank=True, default=list)),
                ("safe_payload", models.JSONField(blank=True, default=dict)),
                ("retrieved_at", models.DateTimeField(blank=True, null=True)),
                ("confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("confirmed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="confirmed_property_enrichments", to=settings.AUTH_USER_MODEL)),
                ("property", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="enrichment", to="properties.property")),
            ],
            options={
                "ordering": ["-updated_at"],
            },
        ),
    ]
