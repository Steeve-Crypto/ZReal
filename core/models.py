from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    """
    Extended user profile for ZReal roles and SaaS features.
    """
    ROLE_CHOICES = [
        ('investor', 'Investor'),
        ('issuer', 'Issuer'),
        ('admin', 'Admin'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='investor')
    
    # SaaS / Billing
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
    subscription_status = models.CharField(max_length=50, default='inactive')  # active, past_due, canceled, etc.
    current_plan = models.CharField(max_length=50, blank=True, null=True)  # e.g. 'issuer_pro'
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"

    @property
    def is_issuer(self):
        return self.role == 'issuer'

    @property
    def is_investor(self):
        return self.role == 'investor'

    @property
    def has_active_subscription(self):
        return self.subscription_status == 'active'


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
