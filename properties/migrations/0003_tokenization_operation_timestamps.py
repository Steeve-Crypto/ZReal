from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0002_tokenization_metadata_document_hash'),
    ]

    operations = [
        migrations.AddField(
            model_name='tokenizationoperation',
            name='broadcast_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='tokenizationoperation',
            name='failed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
