from __future__ import annotations

import logging
from datetime import datetime, timezone

import requests
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from .models import Trip
from .serializers import TripPlanRequestSerializer, TripSerializer
from .services.geocoding import GeocodingError, geocode
from .services.hos_planner import HOSConfig, HOSPlanner, RouteLeg
from .services.routing import RoutingError, route_between

log = logging.getLogger(__name__)


def _resolve_location(payload: dict) -> dict:
    # If the FE already gave us a lat/lon (autocomplete selection), skip the
    # geocode call.
    if "latitude" in payload and "longitude" in payload and not payload.get("query"):
        return {
            "label": payload.get("label") or f"{payload['latitude']:.5f}, {payload['longitude']:.5f}",
            "latitude": float(payload["latitude"]),
            "longitude": float(payload["longitude"]),
        }

    query = payload.get("query") or payload.get("label") or ""
    result = geocode(query)
    return {
        "label": payload.get("label") or result.label,
        "latitude": result.latitude,
        "longitude": result.longitude,
    }


@api_view(["POST"])
@throttle_classes([AnonRateThrottle])
def plan_trip(request):
    serializer = TripPlanRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        current = _resolve_location(data["current_location"])
        pickup = _resolve_location(data["pickup_location"])
        dropoff = _resolve_location(data["dropoff_location"])
    except GeocodingError as exc:
        return Response(
            {"error": "geocoding_failed", "detail": str(exc)},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    # One OSRM call for current → pickup → dropoff so the geometry stays
    # consistent; we split it at the pickup point afterwards.
    try:
        full_route = route_between(
            [
                (current["latitude"], current["longitude"]),
                (pickup["latitude"], pickup["longitude"]),
                (dropoff["latitude"], dropoff["longitude"]),
            ]
        )
    except RoutingError as exc:
        return Response(
            {"error": "routing_failed", "detail": str(exc)},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    if len(full_route.legs) < 2:
        return Response(
            {
                "error": "routing_failed",
                "detail": "Router returned fewer legs than expected.",
            },
            status=status.HTTP_502_BAD_GATEWAY,
        )

    polyline_full = full_route.geometry
    leg_to_pickup_polyline, leg_to_dropoff_polyline = _split_polyline_at_pickup(
        polyline_full, (pickup["latitude"], pickup["longitude"])
    )

    leg_to_pickup = RouteLeg(
        distance_miles=full_route.legs[0].distance_miles,
        duration_seconds=full_route.legs[0].duration_seconds,
        polyline=leg_to_pickup_polyline,
    )
    leg_to_dropoff = RouteLeg(
        distance_miles=full_route.legs[1].distance_miles,
        duration_seconds=full_route.legs[1].duration_seconds,
        polyline=leg_to_dropoff_polyline,
    )

    departure_at = data.get("departure_at") or datetime.now(tz=timezone.utc)
    planner = HOSPlanner(HOSConfig())
    plan = planner.plan(
        departure_at=departure_at,
        current_cycle_hours=data["current_cycle_hours"],
        current_label=current["label"],
        pickup_label=pickup["label"],
        dropoff_label=dropoff["label"],
        current_lat=current["latitude"],
        current_lon=current["longitude"],
        pickup_lat=pickup["latitude"],
        pickup_lon=pickup["longitude"],
        dropoff_lat=dropoff["latitude"],
        dropoff_lon=dropoff["longitude"],
        leg_to_pickup=leg_to_pickup,
        leg_to_dropoff=leg_to_dropoff,
    )

    payload = {
        "inputs": {
            "current_location": current,
            "pickup_location": pickup,
            "dropoff_location": dropoff,
            "current_cycle_hours": data["current_cycle_hours"],
            "departure_at": departure_at.isoformat(),
        },
        "route": {
            "full_geometry": full_route.geometry,
            "total_distance_miles": round(full_route.total_distance_miles, 2),
            "total_duration_seconds": round(full_route.total_duration_seconds, 2),
            "legs": [
                {
                    "distance_miles": round(leg.distance_miles, 2),
                    "duration_seconds": round(leg.duration_seconds, 2),
                    "summary": leg.summary,
                }
                for leg in full_route.legs
            ],
        },
        "plan": plan,
    }

    trip = Trip.objects.create(
        current_location_label=current["label"],
        current_location_lat=current["latitude"],
        current_location_lon=current["longitude"],
        pickup_location_label=pickup["label"],
        pickup_location_lat=pickup["latitude"],
        pickup_location_lon=pickup["longitude"],
        dropoff_location_label=dropoff["label"],
        dropoff_location_lat=dropoff["latitude"],
        dropoff_location_lon=dropoff["longitude"],
        current_cycle_hours=data["current_cycle_hours"],
        departure_at=departure_at,
        total_distance_miles=plan["summary"]["total_distance_miles"],
        total_drive_minutes=int(plan["summary"]["total_drive_minutes"]),
        total_on_duty_minutes=int(plan["summary"]["total_on_duty_not_driving_minutes"]),
        total_off_duty_minutes=int(plan["summary"]["total_off_duty_minutes"]),
        total_sleeper_minutes=int(plan["summary"]["total_sleeper_berth_minutes"]),
        total_trip_minutes=int(plan["summary"]["total_trip_minutes"]),
        number_of_days=plan["summary"]["number_of_days"],
        plan_payload=payload,
    )

    payload["trip_id"] = trip.id
    return Response(payload, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def get_trip(_request, trip_id: int):
    try:
        trip = Trip.objects.get(pk=trip_id)
    except Trip.DoesNotExist:
        return Response({"error": "not_found"}, status=status.HTTP_404_NOT_FOUND)
    return Response(TripSerializer(trip).data)


@api_view(["GET"])
def list_trips(_request):
    qs = Trip.objects.all()[:50]
    data = [
        {
            "id": t.id,
            "created_at": t.created_at,
            "current_location_label": t.current_location_label,
            "pickup_location_label": t.pickup_location_label,
            "dropoff_location_label": t.dropoff_location_label,
            "total_distance_miles": t.total_distance_miles,
            "number_of_days": t.number_of_days,
        }
        for t in qs
    ]
    return Response(data)


@api_view(["GET"])
@throttle_classes([AnonRateThrottle])
def geocode_search(request):
    q = (request.GET.get("q") or "").strip()
    if not q or len(q) < 3:
        return Response([])
    url = f"{settings.NOMINATIM_BASE_URL.rstrip('/')}/search"
    params = {
        "q": q,
        "format": "jsonv2",
        "addressdetails": 1,
        "limit": 5,
    }
    headers = {
        "User-Agent": settings.HTTP_USER_AGENT,
        "Accept": "application/json",
        "Accept-Language": "en",
    }
    try:
        r = requests.get(
            url, params=params, headers=headers, timeout=settings.HTTP_TIMEOUT_SECONDS
        )
        r.raise_for_status()
    except requests.RequestException as exc:
        log.warning("Geocode search failed: %s", exc)
        return Response(
            {"error": "geocoding_failed", "detail": str(exc)},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    try:
        rows = r.json()
    except ValueError:
        return Response({"error": "bad_geocoder_response"}, status=status.HTTP_502_BAD_GATEWAY)

    return Response(
        [
            {
                "label": row.get("display_name"),
                "latitude": float(row["lat"]),
                "longitude": float(row["lon"]),
                "type": row.get("type"),
                "class": row.get("class"),
            }
            for row in rows
            if "lat" in row and "lon" in row
        ]
    )


def _split_polyline_at_pickup(
    polyline: list[list[float]], pickup_latlon: tuple[float, float]
) -> tuple[list[list[float]], list[list[float]]]:
    if not polyline:
        return [], []
    pickup_lat, pickup_lon = pickup_latlon
    best_idx = 0
    best_d = float("inf")
    for i, (lon, lat) in enumerate(polyline):
        d = (lat - pickup_lat) ** 2 + (lon - pickup_lon) ** 2
        if d < best_d:
            best_d = d
            best_idx = i
    head = polyline[: best_idx + 1]
    tail = polyline[best_idx:]
    if not head:
        head = [polyline[0]]
    if not tail:
        tail = [polyline[-1]]
    return head, tail
