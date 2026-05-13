from __future__ import annotations

from django.db import models


class Trip(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    current_location_label = models.CharField(max_length=255)
    current_location_lat = models.FloatField()
    current_location_lon = models.FloatField()

    pickup_location_label = models.CharField(max_length=255)
    pickup_location_lat = models.FloatField()
    pickup_location_lon = models.FloatField()

    dropoff_location_label = models.CharField(max_length=255)
    dropoff_location_lat = models.FloatField()
    dropoff_location_lon = models.FloatField()

    current_cycle_hours = models.FloatField(
        help_text="Hours already used in the rolling 70-hour / 8-day cycle."
    )

    departure_at = models.DateTimeField(
        help_text="Local-time clock the planner started from."
    )

    total_distance_miles = models.FloatField(default=0)
    total_drive_minutes = models.IntegerField(default=0)
    total_on_duty_minutes = models.IntegerField(default=0)
    total_off_duty_minutes = models.IntegerField(default=0)
    total_sleeper_minutes = models.IntegerField(default=0)
    total_trip_minutes = models.IntegerField(default=0)
    number_of_days = models.IntegerField(default=1)

    plan_payload = models.JSONField()

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return (
            f"Trip #{self.pk}: {self.pickup_location_label} → "
            f"{self.dropoff_location_label} ({self.total_distance_miles:.0f} mi)"
        )
