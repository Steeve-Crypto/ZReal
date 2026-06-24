"""
External Property Valuation Service

This module is designed to be adaptable.
You can easily swap the implementation to use different APIs:
- RapidAPI Real Estate APIs
- ATTOM Data
- Zillow-like APIs (via partners)
- Custom internal ML models
- etc.

Current implementation: Heuristic fallback + placeholder for external API.
"""

import requests
from decimal import Decimal
from django.conf import settings


class ExternalValuationService:
    """
    Adaptable external valuation service.
    """
    
    def __init__(self):
        self.api_key = getattr(settings, 'VALUATION_API_KEY', None)
        self.api_url = getattr(settings, 'VALUATION_API_URL', None)
    
    def get_valuation(self, property_obj):
        """
        Main method to get external valuation.
        Falls back to heuristic if no API configured.
        """
        if self.api_key and self.api_url:
            return self._fetch_from_external_api(property_obj)
        else:
            # Fallback to local heuristic
            return property_obj.calculate_valuation(method='heuristic')
    
    def _fetch_from_external_api(self, property_obj):
        """
        Example integration with an external real estate valuation API.
        Replace this with actual API integration.
        """
        try:
            payload = {
                "address": property_obj.location,
                "size_sqm": float(property_obj.size_sqm) if property_obj.size_sqm else None,
                "property_type": "residential",  # Can be extended
            }
            
            headers = {
                "X-RapidAPI-Key": self.api_key,
                "X-RapidAPI-Host": "example-real-estate-api.p.rapidapi.com"
            }
            
            # This is a placeholder URL. Replace with real endpoint.
            response = requests.post(
                f"{self.api_url}/valuate",
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                estimated = Decimal(str(data.get('estimated_value', 0)))
                
                # Update property
                property_obj.estimated_value = estimated
                property_obj.valuation_method = 'external_api'
                property_obj.valuation_confidence = data.get('confidence', 0.75)
                property_obj.last_valued_at = timezone.now()
                property_obj.valuation_notes = f"External API valuation. Source: {data.get('source', 'unknown')}"
                property_obj.save()
                
                # Save history
                from .models import PropertyValuationHistory
                PropertyValuationHistory.objects.create(
                    property=property_obj,
                    estimated_value=estimated,
                    valuation_method='external_api',
                    confidence=property_obj.valuation_confidence,
                    notes=property_obj.valuation_notes
                )
                
                return estimated
            
        except Exception as e:
            print(f"[Valuation] External API failed: {e}")
        
        # Fallback
        return property_obj.calculate_valuation(method='heuristic')
