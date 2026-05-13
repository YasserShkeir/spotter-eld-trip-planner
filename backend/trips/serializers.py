from __future__ import annotations

from rest_framework import serializers

from .models import Trip


class LocationInputSerializer(serializers.Serializer):
    """Free-text ``query`` to geocode, or pre-resolved label + lat + lon."""

    query = serializers.CharField(required=False, allow_blank=True, max_length=255)
    label = serializers.CharField(required=False, allow_blank=True, max_length=255)
    latitude = serializers.FloatField(required=False)
    longitude = serializers.FloatField(required=False)

    def validate(self, attrs):
        has_query = bool(attrs.get("query", "").strip())
        has_latlon = "latitude" in attrs and "longitude" in attrs
        if not has_query and not has_latlon:
            raise serializers.ValidationError(
                "Provide either `query` (address) or `latitude` + `longitude`."
            )
        if has_latlon:
            lat = attrs["latitude"]
            lon = attrs["longitude"]
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                raise serializers.ValidationError("Latitude/longitude out of range.")
        return attrs


class TripPlanRequestSerializer(serializers.Serializer):
    current_location = LocationInputSerializer()
    pickup_location = LocationInputSerializer()
    dropoff_location = LocationInputSerializer()
    current_cycle_hours = serializers.FloatField(min_value=0, max_value=70)
    departure_at = serializers.DateTimeField(required=False)


class TripSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = [
            "id",
            "created_at",
            "current_location_label",
            "current_location_lat",
            "current_location_lon",
            "pickup_location_label",
            "pickup_location_lat",
            "pickup_location_lon",
            "dropoff_location_label",
            "dropoff_location_lat",
            "dropoff_location_lon",
            "current_cycle_hours",
            "departure_at",
            "total_distance_miles",
            "total_drive_minutes",
            "total_on_duty_minutes",
            "total_off_duty_minutes",
            "total_sleeper_minutes",
            "total_trip_minutes",
            "number_of_days",
            "plan_payload",
        ]
        read_only_fields = fields
