from django.contrib import admin

from .models import Trip


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "pickup_location_label",
        "dropoff_location_label",
        "total_distance_miles",
        "number_of_days",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = (
        "current_location_label",
        "pickup_location_label",
        "dropoff_location_label",
    )
    readonly_fields = ("created_at", "updated_at", "plan_payload")
