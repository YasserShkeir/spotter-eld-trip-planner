from __future__ import annotations

from datetime import datetime, timezone

from django.test import SimpleTestCase

from trips.services.hos_planner import HOSConfig, HOSPlanner, RouteLeg


def _make_polyline(lat1: float, lon1: float, lat2: float, lon2: float, steps: int = 50):
    return [
        [
            lon1 + (lon2 - lon1) * (i / steps),
            lat1 + (lat2 - lat1) * (i / steps),
        ]
        for i in range(steps + 1)
    ]


class HOSPlannerTests(SimpleTestCase):
    def setUp(self):
        self.planner = HOSPlanner(HOSConfig())
        self.departure = datetime(2025, 1, 6, 6, 0, 0, tzinfo=timezone.utc)

    def _plan(self, *, pickup_miles, dropoff_miles, cycle_hours=10.0):
        leg1 = RouteLeg(
            distance_miles=pickup_miles,
            duration_seconds=pickup_miles * 60,  # 60 mph
            polyline=_make_polyline(40.0, -74.0, 40.5, -75.0),
        )
        leg2 = RouteLeg(
            distance_miles=dropoff_miles,
            duration_seconds=dropoff_miles * 60,
            polyline=_make_polyline(40.5, -75.0, 41.0, -77.0),
        )
        return self.planner.plan(
            departure_at=self.departure,
            current_cycle_hours=cycle_hours,
            current_label="Origin",
            pickup_label="Pickup",
            dropoff_label="Drop-off",
            current_lat=40.0,
            current_lon=-74.0,
            pickup_lat=40.5,
            pickup_lon=-75.0,
            dropoff_lat=41.0,
            dropoff_lon=-77.0,
            leg_to_pickup=leg1,
            leg_to_dropoff=leg2,
        )

    def test_short_trip_no_break_needed(self):
        plan = self._plan(pickup_miles=50, dropoff_miles=100)
        statuses = [s["status"] for s in plan["plan"]["segments"]] if "plan" in plan else [
            s["status"] for s in plan["segments"]
        ]
        self.assertIn("driving", statuses)
        self.assertIn("on_duty_not_driving", statuses)
        # No long sleeper berth on a ~2.5hr trip
        long_rest = [
            s for s in plan["segments"]
            if s["status"] == "sleeper_berth" and s["duration_minutes"] >= 600
        ]
        self.assertEqual(long_rest, [])
        self.assertGreater(plan["summary"]["total_distance_miles"], 140)
        self.assertGreaterEqual(plan["summary"]["number_of_days"], 1)

    def test_long_trip_inserts_30min_break_after_8_drive_hours(self):
        plan = self._plan(pickup_miles=10, dropoff_miles=600)  # ~10hr+ of driving
        breaks = [
            s for s in plan["segments"]
            if s["status"] == "off_duty" and "30-minute" in s["description"]
        ]
        self.assertGreaterEqual(len(breaks), 1, "Expected at least one 30-minute break")

    def test_very_long_trip_inserts_10hr_rest(self):
        plan = self._plan(pickup_miles=10, dropoff_miles=900)  # > 11hr drive
        rests = [
            s for s in plan["segments"]
            if s["status"] == "sleeper_berth" and s["duration_minutes"] >= 600
        ]
        self.assertGreaterEqual(len(rests), 1, "Expected a 10-hour sleeper berth rest")

    def test_high_cycle_triggers_restart(self):
        # Driver already has 69hrs in the cycle, trip is non-trivial → restart required.
        plan = self._plan(pickup_miles=10, dropoff_miles=300, cycle_hours=69.0)
        restarts = [
            s for s in plan["segments"]
            if s["status"] == "off_duty" and "34-hour" in s["description"]
        ]
        self.assertGreaterEqual(len(restarts), 1, "Expected a 34-hour restart")

    def test_fuel_stop_inserted_every_1000_miles(self):
        plan = self._plan(pickup_miles=10, dropoff_miles=1500)  # > 1000 miles
        fuel_stops = [
            st for st in plan["stops"] if st["kind"] == "fuel"
        ]
        self.assertGreaterEqual(len(fuel_stops), 1, "Expected at least one fuel stop")

    def test_daily_grids_sum_to_24_hours(self):
        plan = self._plan(pickup_miles=10, dropoff_miles=400)
        for day in plan["days"]:
            total = sum(day["totals"].values())
            self.assertAlmostEqual(total, 24 * 60, places=0, msg=f"Day {day['date']} totals: {day['totals']}")

    def test_pickup_and_dropoff_present(self):
        plan = self._plan(pickup_miles=50, dropoff_miles=50)
        pickup_stop = [st for st in plan["stops"] if st["kind"] == "pickup"]
        dropoff_stop = [st for st in plan["stops"] if st["kind"] == "dropoff"]
        self.assertEqual(len(pickup_stop), 1)
        self.assertEqual(len(dropoff_stop), 1)
        self.assertAlmostEqual(pickup_stop[0]["duration_minutes"], 60, places=0)
        self.assertAlmostEqual(dropoff_stop[0]["duration_minutes"], 60, places=0)
