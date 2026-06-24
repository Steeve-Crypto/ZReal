from allauth.account.forms import SignupForm
from django import forms
from .models import UserProfile

class SignupForm(SignupForm):
    """
    Custom signup form that lets users choose their role (Issuer or Investor).
    """
    ROLE_CHOICES = [
        ('investor', 'I want to invest in real estate (Investor)'),
        ('issuer', 'I want to tokenize my properties (Issuer)'),
    ]
    
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.RadioSelect,
        label="What would you like to do on ZReal?",
        initial='investor'
    )

    def save(self, request):
        user = super().save(request)
        # Set role from form
        user.profile.role = self.cleaned_data['role']
        user.profile.save()
        return user
