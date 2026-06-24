from django.http import JsonResponse
import joblib
import numpy as np

# Simple pre-trained model stub (train on real data in production)
# For demo: Random prediction based on size
def predict_property_value(request):
    size = float(request.GET.get('size_sqm', 100))
    bedrooms = int(request.GET.get('bedrooms', 2))
    
    # Placeholder ML logic (replace with real model)
    base_price = size * 2500  # $ per sqm rough estimate
    bedroom_bonus = bedrooms * 15000
    predicted = base_price + bedroom_bonus + np.random.randint(-20000, 20000)
    
    return JsonResponse({
        'predicted_value_usd': round(predicted, 2),
        'confidence': 'demo-mode (train real model with scikit-learn)',
        'features_used': ['size_sqm', 'bedrooms', 'location (future PostGIS features)']
    })
