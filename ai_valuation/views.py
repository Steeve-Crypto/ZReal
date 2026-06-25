from django.http import JsonResponse
from decimal import Decimal

def predict_property_value(request):
    size = Decimal(str(request.GET.get('size_sqm', 100)))
    bedrooms = int(request.GET.get('bedrooms', 2))
    bathrooms = int(request.GET.get('bathrooms', 1))

    predicted = (size * Decimal('2500')) + Decimal(bedrooms * 15000) + Decimal(bathrooms * 10000)
    
    return JsonResponse({
        'predicted_value_usd': round(predicted, 2),
        'method': 'deterministic heuristic',
        'features_used': ['size_sqm', 'bedrooms', 'bathrooms']
    })
