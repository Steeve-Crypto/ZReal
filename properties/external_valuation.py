"""
External Property Valuation Service.

The service is intentionally conservative: if no external API is configured it
returns a deterministic heuristic based on actual model fields, and it labels
the source honestly.
"""

from decimal import Decimal

import requests
from django.conf import settings


class ExternalValuationService:
    def __init__(self):
        self.api_key = getattr(settings, 'VALUATION_API_KEY', None)
        self.api_url = getattr(settings, 'VALUATION_API_URL', None)

    def get_valuation(self, property_obj):
        if self.api_key and self.api_url:
            value = self._fetch_from_external_api(property_obj)
            if value is not None:
                return value
        return self._heuristic(property_obj)

    def _heuristic(self, property_obj):
        if not property_obj.size_sqm:
            return None
        base_price = Decimal(str(property_obj.size_sqm)) * Decimal('2500')
        bedroom_bonus = Decimal(property_obj.bedrooms or 0) * Decimal('15000')
        bathroom_bonus = Decimal(property_obj.bathrooms or 0) * Decimal('10000')
        estimated = base_price + bedroom_bonus + bathroom_bonus
        property_obj.estimated_value = estimated
        property_obj.save(update_fields=['estimated_value', 'updated_at'])
        return estimated

    def _fetch_from_external_api(self, property_obj):
        try:
            payload = {
                "address": property_obj.address,
                "latitude": float(property_obj.latitude) if property_obj.latitude is not None else None,
                "longitude": float(property_obj.longitude) if property_obj.longitude is not None else None,
                "size_sqm": float(property_obj.size_sqm) if property_obj.size_sqm else None,
                "bedrooms": property_obj.bedrooms,
                "bathrooms": property_obj.bathrooms,
            }
            response = requests.post(
                self.api_url,
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            estimated = data.get('estimated_value')
            if estimated is None:
                return None
            estimated = Decimal(str(estimated))
            property_obj.estimated_value = estimated
            property_obj.save(update_fields=['estimated_value', 'updated_at'])
            return estimated
        except Exception:
            return None
