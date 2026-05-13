from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any

import requests
from django.conf import settings

log = logging.getLogger(__name__)

_cache: dict[str, "GeocodeResult"] = {}
_cache_lock = threading.Lock()


class GeocodingError(Exception):
    pass


@dataclass(frozen=True)
class GeocodeResult:
    label: str
    latitude: float
    longitude: float
    raw: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "latitude": self.latitude,
            "longitude": self.longitude,
        }


def geocode(query: str) -> GeocodeResult:
    if not query or not query.strip():
        raise GeocodingError("Empty query")

    key = query.strip().lower()
    with _cache_lock:
        cached = _cache.get(key)
        if cached is not None:
            return cached

    url = f"{settings.NOMINATIM_BASE_URL.rstrip('/')}/search"
    params = {
        "q": query,
        "format": "jsonv2",
        "addressdetails": 1,
        "limit": 1,
    }
    headers = {
        "User-Agent": settings.HTTP_USER_AGENT,
        "Accept": "application/json",
        "Accept-Language": "en",
    }

    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=settings.HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        log.warning("Nominatim request failed for %r: %s", query, exc)
        raise GeocodingError(f"Could not reach geocoder: {exc}") from exc

    try:
        results = response.json()
    except ValueError as exc:
        raise GeocodingError("Geocoder returned invalid JSON") from exc

    if not results:
        raise GeocodingError(f"No location found for {query!r}")

    top = results[0]
    try:
        result = GeocodeResult(
            label=top.get("display_name") or query,
            latitude=float(top["lat"]),
            longitude=float(top["lon"]),
            raw=top,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise GeocodingError("Geocoder returned malformed payload") from exc

    with _cache_lock:
        _cache[key] = result
    return result
