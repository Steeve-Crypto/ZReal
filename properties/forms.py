from django import forms

from .models import Property


class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = [
            'title',
            'description',
            'address',
            'latitude',
            'longitude',
            'size_sqm',
            'bedrooms',
            'bathrooms',
            'estimated_value',
            'total_shares',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ("title", "size_sqm", "total_shares"):
            self.fields[field_name].required = False

    def clean_title(self):
        title = (self.cleaned_data.get('title') or '').strip()
        address = self.data.get('address', '').strip()
        return title or address or 'Untitled property'

    def clean_total_shares(self):
        return self.cleaned_data.get('total_shares') or 10000

    def clean(self):
        cleaned = super().clean()
        latitude = cleaned.get('latitude')
        longitude = cleaned.get('longitude')
        if (latitude is None) != (longitude is None):
            raise forms.ValidationError('Latitude and longitude must be provided together.')
        return cleaned
