from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def create_profiles(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    UserProfile = apps.get_model('core', 'UserProfile')
    for user in User.objects.all():
        UserProfile.objects.get_or_create(user=user)


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('investor', 'Investor'), ('issuer', 'Issuer'), ('admin', 'Admin')], default='investor', max_length=20)),
                ('stripe_customer_id', models.CharField(blank=True, max_length=100, null=True)),
                ('subscription_status', models.CharField(default='inactive', max_length=50)),
                ('current_plan', models.CharField(blank=True, max_length=50, null=True)),
                ('default_viewing_key', models.TextField(blank=True, help_text='Exported Sapling viewing key for read-only portfolio access', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.RunPython(create_profiles, migrations.RunPython.noop),
    ]
