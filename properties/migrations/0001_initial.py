from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Property',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('address', models.CharField(max_length=500)),
                ('latitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('longitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('plot_geojson', models.JSONField(blank=True, default=dict, help_text='Optional plot boundary GeoJSON')),
                ('size_sqm', models.FloatField(help_text='Total size in square meters')),
                ('bedrooms', models.PositiveIntegerField(blank=True, null=True)),
                ('bathrooms', models.PositiveIntegerField(blank=True, null=True)),
                ('estimated_value', models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True)),
                ('total_shares', models.PositiveIntegerField(default=10000, help_text='Total fractional shares / ZSA tokens')),
                ('zsa_asset_id', models.CharField(blank=True, help_text='Zcash Shielded Asset identifier once issued', max_length=100, null=True)),
                ('zcash_operation_id', models.CharField(blank=True, max_length=128, null=True)),
                ('zcash_txid', models.CharField(blank=True, max_length=128, null=True)),
                ('tokenization_status', models.CharField(choices=[('not_started', 'Not Started'), ('pending', 'Pending'), ('broadcast', 'Broadcast'), ('confirmed', 'Confirmed'), ('failed', 'Failed')], default='not_started', max_length=20)),
                ('tokenization_error', models.TextField(blank=True)),
                ('tokenized_at', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('tokenizing', 'Tokenizing'), ('tokenized', 'Tokenized (ZSA Issued)'), ('active', 'Active - Open for Investment')], default='draft', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='owned_properties', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PropertyDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='property_documents/')),
                ('document_type', models.CharField(blank=True, help_text='e.g. Deed, Title, Contract, Appraisal', max_length=100)),
                ('extracted_text', models.TextField(blank=True)),
                ('extracted_data', models.JSONField(blank=True, default=dict)),
                ('ocr_confidence', models.FloatField(blank=True, null=True)),
                ('processing_status', models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
                ('property', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='properties.property')),
            ],
        ),
        migrations.CreateModel(
            name='PropertyInvestment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('shares_owned', models.PositiveIntegerField()),
                ('purchase_tx_hash', models.CharField(blank=True, help_text='Zcash shielded tx hash', max_length=100)),
                ('purchase_date', models.DateTimeField(auto_now_add=True)),
                ('investor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('property', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='investments', to='properties.property')),
            ],
            options={
                'unique_together': {('investor', 'property')},
            },
        ),
        migrations.CreateModel(
            name='TokenizationOperation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('issuer_zaddr', models.CharField(max_length=256)),
                ('asset_symbol', models.CharField(max_length=64)),
                ('total_shares', models.PositiveIntegerField()),
                ('backend', models.CharField(max_length=64)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('broadcast', 'Broadcast'), ('confirmed', 'Confirmed'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('operation_id', models.CharField(blank=True, max_length=128)),
                ('txid', models.CharField(blank=True, max_length=128)),
                ('asset_id', models.CharField(blank=True, max_length=128)),
                ('error', models.TextField(blank=True)),
                ('response', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('confirmed_at', models.DateTimeField(blank=True, null=True)),
                ('issuer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tokenization_operations', to=settings.AUTH_USER_MODEL)),
                ('property', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tokenization_operations', to='properties.property')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
