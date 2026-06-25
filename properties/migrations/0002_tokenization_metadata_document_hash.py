from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='propertydocument',
            name='file_sha256',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name='tokenizationoperation',
            name='last_status_refreshed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='tokenizationoperation',
            name='metadata',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
