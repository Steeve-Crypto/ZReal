from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from django.conf import settings
from django.utils import timezone

from .models import PropertyEnrichment


CONFIDENCE_REVIEW_THRESHOLD = Decimal("0.8000")


class PropertyDataProviderError(RuntimeError):
    code = "provider_error"


class ProviderDisabled(PropertyDataProviderError):
    code = "provider_disabled"


class ProviderMissingConfiguration(PropertyDataProviderError):
    code = "missing_provider_configuration"


class ProviderUnsupported(PropertyDataProviderError):
    code = "unsupported_provider"


@dataclass
class PropertyCandidate:
    normalized_address: str
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    match_confidence: Decimal | None = None
    address_line_1: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = "US"
    county: str = ""
    jurisdiction: str = ""
    parcel_id: str = ""
    apn: str = ""
    lot_size: Decimal | None = None
    building_area: Decimal | None = None
    year_built: int | None = None
    property_type: str = ""
    assessed_value: Decimal | None = None
    tax_value: Decimal | None = None
    source_record_id: str = ""
    data_source: str = ""
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    def to_safe_dict(self):
        data = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Decimal):
                data[key] = str(value)
            else:
                data[key] = value
        return data


@dataclass
class PropertyDataResult:
    provider: str
    candidates: list[PropertyCandidate]
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    @property
    def best_candidate(self):
        return self.candidates[0] if self.candidates else None


class BasePropertyDataProvider:
    slug = "base"
    data_source = "Unspecified provider"

    def resolve_address(self, address: str) -> PropertyDataResult:
        raise NotImplementedError


def decimal_or_none(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


class MockPropertyDataProvider(BasePropertyDataProvider):
    slug = "mock"
    data_source = "ZReal address reference data"

    def resolve_address(self, address: str) -> PropertyDataResult:
        normalized = " ".join(address.split()).strip()
        if not normalized:
            return PropertyDataResult(self.slug, [], blockers=["Address is required."])
        lowered = normalized.lower()
        confidence = Decimal("0.6200") if "ambiguous" in lowered or "low confidence" in lowered else Decimal("0.9400")
        candidate = PropertyCandidate(
            normalized_address=normalized.title(),
            latitude=Decimal("38.897700"),
            longitude=Decimal("-77.036500"),
            match_confidence=confidence,
            address_line_1=normalized.title(),
            city="Washington",
            state="DC",
            postal_code="20500",
            county="District of Columbia",
            jurisdiction="District of Columbia",
            source_record_id="local-reference-001",
            data_source=self.data_source,
            warnings=[] if confidence >= CONFIDENCE_REVIEW_THRESHOLD else ["Low confidence address match; issuer review required."],
        )
        candidates = [candidate]
        if "ambiguous" in lowered:
            alt = PropertyCandidate(
                normalized_address=f"{normalized.title()} Unit 2",
                latitude=Decimal("38.897800"),
                longitude=Decimal("-77.036600"),
                match_confidence=Decimal("0.5800"),
                data_source=self.data_source,
                source_record_id="local-reference-002",
                warnings=["Alternate address candidate."],
            )
            candidates.append(alt)
        return PropertyDataResult(self.slug, candidates, warnings=candidate.warnings)


class CensusGeocoderProvider(BasePropertyDataProvider):
    slug = "census"
    data_source = "US Census Geocoder"

    def resolve_address(self, address: str) -> PropertyDataResult:
        if not settings.PROPERTY_DATA_ENABLE_LIVE_CALLS:
            raise ProviderDisabled("Live property data calls are disabled.")
        params = urlencode({"address": address, "benchmark": "Public_AR_Current", "format": "json"})
        url = f"https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?{params}"
        try:
            with urlopen(url, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise PropertyDataProviderError(f"Census geocoder returned HTTP {exc.code}.") from exc
        except (URLError, TimeoutError) as exc:
            raise PropertyDataProviderError("Census geocoder is unavailable.") from exc
        matches = payload.get("result", {}).get("addressMatches", [])
        candidates = []
        for match in matches[:5]:
            coords = match.get("coordinates") or {}
            candidates.append(PropertyCandidate(
                normalized_address=match.get("matchedAddress", ""),
                latitude=decimal_or_none(coords.get("y")),
                longitude=decimal_or_none(coords.get("x")),
                match_confidence=Decimal("0.9000") if len(matches) == 1 else Decimal("0.7000"),
                source_record_id=str(match.get("tigerLine", {}).get("tigerLineId", "")),
                data_source=self.data_source,
                warnings=[] if len(matches) == 1 else ["Multiple Census geocoder candidates require issuer review."],
            ))
        blockers = [] if candidates else ["No Census geocoder match found."]
        return PropertyDataResult(self.slug, candidates, blockers=blockers)


class KeyedPlaceholderProvider(BasePropertyDataProvider):
    required_setting = ""

    def resolve_address(self, address: str) -> PropertyDataResult:
        if not getattr(settings, self.required_setting, ""):
            raise ProviderMissingConfiguration(f"{self.required_setting} is required for {self.slug}.")
        if not settings.PROPERTY_DATA_ENABLE_LIVE_CALLS:
            raise ProviderDisabled("Live property data calls are disabled.")
        raise ProviderDisabled(f"{self.slug} live adapter is not implemented yet.")


class RegridProvider(KeyedPlaceholderProvider):
    slug = "regrid"
    data_source = "Regrid parcel API"
    required_setting = "PROPERTY_DATA_REGRID_API_KEY"


class OpenCageProvider(KeyedPlaceholderProvider):
    slug = "opencage"
    data_source = "OpenCage geocoder"
    required_setting = "PROPERTY_DATA_OPENCAGE_API_KEY"


class GoogleProvider(KeyedPlaceholderProvider):
    slug = "google"
    data_source = "Google geocoding"
    required_setting = "PROPERTY_DATA_GOOGLE_API_KEY"


PROVIDERS = {
    "mock": MockPropertyDataProvider,
    "fixture": MockPropertyDataProvider,
    "census": CensusGeocoderProvider,
    "regrid": RegridProvider,
    "opencage": OpenCageProvider,
    "google": GoogleProvider,
}


def get_property_data_provider():
    provider_name = settings.PROPERTY_DATA_PROVIDER.lower()
    provider_class = PROVIDERS.get(provider_name)
    if not provider_class:
        raise ProviderUnsupported(f"Unsupported property data provider: {settings.PROPERTY_DATA_PROVIDER}")
    return provider_class()


def status_for_result(result: PropertyDataResult):
    if result.blockers or not result.best_candidate:
        return "failed"
    if len(result.candidates) > 1:
        return "needs_review"
    confidence = result.best_candidate.match_confidence
    if confidence is not None and confidence < CONFIDENCE_REVIEW_THRESHOLD:
        return "needs_review"
    return "enriched"


def store_enrichment_result(prop, result: PropertyDataResult):
    candidate = result.best_candidate
    enrichment, _ = PropertyEnrichment.objects.get_or_create(property=prop)
    enrichment.status = status_for_result(result)
    enrichment.provider = result.provider
    enrichment.retrieved_at = timezone.now()
    enrichment.confirmed_at = None
    enrichment.confirmed_by = None
    enrichment.warnings = list(result.warnings)
    enrichment.blockers = list(result.blockers)
    enrichment.candidates = [item.to_safe_dict() for item in result.candidates]
    enrichment.safe_payload = candidate.to_safe_dict() if candidate else {}
    if candidate:
        for field_name in [
            "normalized_address", "address_line_1", "city", "state", "postal_code", "country",
            "county", "jurisdiction", "latitude", "longitude", "parcel_id", "apn", "lot_size",
            "building_area", "year_built", "property_type", "assessed_value", "tax_value",
            "source_record_id", "data_source", "match_confidence",
        ]:
            setattr(enrichment, field_name, getattr(candidate, field_name))
    enrichment.save()
    return enrichment


def store_reviewable_candidate(
    prop,
    *,
    provider: str,
    candidate_data: dict[str, Any],
    candidates: list[dict[str, Any]] | None = None,
    status: str = "needs_review",
    warnings: list[str] | None = None,
    blockers: list[str] | None = None,
):
    """Persist client-reviewed autofill data without marking it trusted."""
    allowed_statuses = {"enriched", "needs_review", "failed"}
    enrichment, _ = PropertyEnrichment.objects.get_or_create(property=prop)
    enrichment.status = status if status in allowed_statuses else "needs_review"
    enrichment.provider = str(provider or "")[:64]
    enrichment.retrieved_at = timezone.now()
    enrichment.confirmed_at = None
    enrichment.confirmed_by = None
    enrichment.warnings = list(warnings or [])
    enrichment.blockers = list(blockers or [])
    enrichment.candidates = list(candidates or ([candidate_data] if candidate_data else []))
    enrichment.safe_payload = dict(candidate_data or {})

    for field_name in [
        "normalized_address", "address_line_1", "city", "state", "postal_code", "country",
        "county", "jurisdiction", "parcel_id", "apn", "property_type", "source_record_id",
        "data_source",
    ]:
        if field_name in candidate_data:
            setattr(enrichment, field_name, str(candidate_data.get(field_name) or ""))

    for field_name in ["latitude", "longitude", "lot_size", "building_area", "assessed_value", "tax_value", "match_confidence"]:
        if field_name in candidate_data:
            setattr(enrichment, field_name, decimal_or_none(candidate_data.get(field_name)))

    if "year_built" in candidate_data:
        try:
            enrichment.year_built = int(candidate_data["year_built"]) if candidate_data.get("year_built") else None
        except (TypeError, ValueError):
            enrichment.year_built = None

    enrichment.save()
    return enrichment


def resolve_property_address(address: str):
    provider = get_property_data_provider()
    return provider.resolve_address(address)


def enrichment_to_payload(enrichment):
    if not enrichment:
        return {
            "status": "not_started",
            "is_confirmed": False,
            "provider": None,
            "normalized_address": None,
            "warnings": [],
            "blockers": [],
            "candidates": [],
        }
    return {
        "id": enrichment.id,
        "status": enrichment.status,
        "is_confirmed": enrichment.is_confirmed,
        "provider": enrichment.provider or None,
        "data_source": enrichment.data_source or None,
        "source_record_id": enrichment.source_record_id or None,
        "normalized_address": enrichment.normalized_address or None,
        "address_line_1": enrichment.address_line_1 or None,
        "city": enrichment.city or None,
        "state": enrichment.state or None,
        "postal_code": enrichment.postal_code or None,
        "country": enrichment.country or None,
        "county": enrichment.county or None,
        "jurisdiction": enrichment.jurisdiction or None,
        "latitude": str(enrichment.latitude) if enrichment.latitude is not None else None,
        "longitude": str(enrichment.longitude) if enrichment.longitude is not None else None,
        "parcel_id": enrichment.parcel_id or None,
        "apn": enrichment.apn or None,
        "lot_size": str(enrichment.lot_size) if enrichment.lot_size is not None else None,
        "building_area": str(enrichment.building_area) if enrichment.building_area is not None else None,
        "year_built": enrichment.year_built,
        "property_type": enrichment.property_type or None,
        "assessed_value": str(enrichment.assessed_value) if enrichment.assessed_value is not None else None,
        "tax_value": str(enrichment.tax_value) if enrichment.tax_value is not None else None,
        "match_confidence": str(enrichment.match_confidence) if enrichment.match_confidence is not None else None,
        "warnings": enrichment.warnings or [],
        "blockers": enrichment.blockers or [],
        "candidates": enrichment.candidates or [],
        "retrieved_at": enrichment.retrieved_at.isoformat() if enrichment.retrieved_at else None,
        "confirmed_at": enrichment.confirmed_at.isoformat() if enrichment.confirmed_at else None,
    }
