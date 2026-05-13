from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import requests
from django.conf import settings

log = logging.getLogger(__name__)

METERS_PER_MILE = 1609.344


class RoutingError(Exception):
    pass


@dataclass(frozen=True)
class RouteLeg:
    distance_miles: float
    duration_seconds: float
    summary: str


@dataclass(frozen=True)
class Route:
    geometry: list[list[float]]
    legs: list[RouteLeg]
    total_distance_miles: float
    total_duration_seconds: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "geometry": self.geometry,
            "legs": [
                {
                    "distance_miles": leg.distance_miles,
                    "duration_seconds": leg.duration_seconds,
                    "summary": leg.summary,
                }
                for leg in self.legs
            ],
            "total_distance_miles": self.total_distance_miles,
            "total_duration_seconds": self.total_duration_seconds,
        }


def route_between(coordinates: list[tuple[float, float]]) -> Route:
    """Route through a list of (latitude, longitude) waypoints."""
    if len(coordinates) < 2:
        raise RoutingError("Need at least two waypoints to plan a route")

    coord_string = ";".join(f"{lon:.6f},{lat:.6f}" for lat, lon in coordinates)
    url = (
        f"{settings.OSRM_BASE_URL.rstrip('/')}"
        f"/route/v1/driving/{coord_string}"
    )
    params = {
        "overview": "full",
        "geometries": "geojson",
        "steps": "false",
        "annotations": "false",
    }
    headers = {
        "User-Agent": settings.HTTP_USER_AGENT,
        "Accept": "application/json",
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
        log.warning("OSRM request failed: %s", exc)
        raise RoutingError(f"Could not reach routing engine: {exc}") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise RoutingError("Router returned invalid JSON") from exc

    if payload.get("code") != "Ok" or not payload.get("routes"):
        raise RoutingError(
            f"Router could not plan a route: {payload.get('code', 'unknown')}"
        )

    route_payload = payload["routes"][0]
    geometry = route_payload.get("geometry", {}).get("coordinates", [])
    if not geometry:
        raise RoutingError("Router returned an empty geometry")

    legs = [
        RouteLeg(
            distance_miles=float(leg["distance"]) / METERS_PER_MILE,
            duration_seconds=float(leg["duration"]),
            summary=leg.get("summary") or "",
        )
        for leg in route_payload.get("legs", [])
    ]

    return Route(
        geometry=geometry,
        legs=legs,
        total_distance_miles=float(route_payload["distance"]) / METERS_PER_MILE,
        total_duration_seconds=float(route_payload["duration"]),
    )
