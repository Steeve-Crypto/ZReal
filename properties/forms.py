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

    def clean(self):
        cleaned = super().clean()
        latitude = cleaned.get('latitude')
        longitude = cleaned.get('longitude')
        if (latitude is None) != (longitude is None):
            raise forms.ValidationError('Latitude and longitude must be provided together.')
        return cleaned
