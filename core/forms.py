from django import forms


class RoleSelectionForm(forms.Form):
    ROLE_CHOICES = [
        ('investor', 'Investor'),
        ('issuer', 'Issuer'),
    ]

    role = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.RadioSelect)
