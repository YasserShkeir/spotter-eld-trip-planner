"""HOS planner for a property-carrying driver on the 70-hr/8-day cycle."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Literal

Status = Literal["off_duty", "sleeper_berth", "driving", "on_duty_not_driving"]

STATUS_LABELS: dict[Status, str] = {
    "off_duty": "Off Duty",
    "sleeper_berth": "Sleeper Berth",
    "driving": "Driving",
    "on_duty_not_driving": "On Duty (Not Driving)",
}

EARTH_RADIUS_MILES = 3958.7613


@dataclass(frozen=True)
class HOSConfig:

    drive_limit_min: int = 11 * 60
    window_limit_min: int = 14 * 60
    cycle_limit_min: int = 70 * 60
    break_after_min: int = 8 * 60
    break_duration_min: int = 30
    rest_duration_min: int = 10 * 60
    restart_duration_min: int = 34 * 60
    pickup_duration_min: int = 60
    dropoff_duration_min: int = 60
    fuel_duration_min: int = 30
    fuel_distance_miles: float = 1000.0


@dataclass
class RouteLeg:
    distance_miles: float
    duration_seconds: float
    polyline: list[list[float]]  # [[lon, lat], ...] OSRM-style


def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_MILES * c


def _interpolate_along(polyline: list[list[float]], target_miles: float) -> tuple[float, float]:
    """Return (lat, lon) at ``target_miles`` along the polyline."""
    if not polyline:
        return 0.0, 0.0
    if target_miles <= 0:
        lon, lat = polyline[0]
        return lat, lon
    cumulative = 0.0
    for i in range(1, len(polyline)):
        lon1, lat1 = polyline[i - 1]
        lon2, lat2 = polyline[i]
        seg = _haversine_miles(lat1, lon1, lat2, lon2)
        if seg <= 0:
            continue
        if cumulative + seg >= target_miles:
            t = (target_miles - cumulative) / seg
            return lat1 + t * (lat2 - lat1), lon1 + t * (lon2 - lon1)
        cumulative += seg
    lon, lat = polyline[-1]
    return lat, lon


@dataclass
class _Segment:
    start: datetime
    end: datetime
    status: Status
    description: str = ""
    start_lat: float | None = None
    start_lon: float | None = None
    end_lat: float | None = None
    end_lon: float | None = None
    distance_miles: float = 0.0

    @property
    def duration_minutes(self) -> float:
        return (self.end - self.start).total_seconds() / 60.0


@dataclass
class _Stop:
    kind: str
    label: str
    arrival: datetime
    departure: datetime
    lat: float
    lon: float
    distance_from_origin_miles: float


class HOSPlanner:

    def __init__(self, cfg: HOSConfig | None = None) -> None:
        self.cfg = cfg or HOSConfig()

    def plan(
        self,
        *,
        departure_at: datetime,
        current_cycle_hours: float,
        current_label: str,
        pickup_label: str,
        dropoff_label: str,
        current_lat: float,
        current_lon: float,
        pickup_lat: float,
        pickup_lon: float,
        dropoff_lat: float,
        dropoff_lon: float,
        leg_to_pickup: RouteLeg,
        leg_to_dropoff: RouteLeg,
    ) -> dict[str, Any]:
        run = _Run(
            cfg=self.cfg,
            departure_at=departure_at,
            current_cycle_hours=current_cycle_hours,
            current_label=current_label,
            pickup_label=pickup_label,
            dropoff_label=dropoff_label,
            current_lat=current_lat,
            current_lon=current_lon,
            pickup_lat=pickup_lat,
            pickup_lon=pickup_lon,
            dropoff_lat=dropoff_lat,
            dropoff_lon=dropoff_lon,
            leg_to_pickup=leg_to_pickup,
            leg_to_dropoff=leg_to_dropoff,
        )
        return run.execute()


@dataclass
class _Leg:
    label: str
    end_label: str
    distance_miles: float
    duration_seconds: float
    polyline: list[list[float]]
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    end_kind: Literal["pickup", "dropoff"]


class _Run:

    def __init__(
        self,
        *,
        cfg: HOSConfig,
        departure_at: datetime,
        current_cycle_hours: float,
        current_label: str,
        pickup_label: str,
        dropoff_label: str,
        current_lat: float,
        current_lon: float,
        pickup_lat: float,
        pickup_lon: float,
        dropoff_lat: float,
        dropoff_lon: float,
        leg_to_pickup: RouteLeg,
        leg_to_dropoff: RouteLeg,
    ) -> None:
        self.cfg = cfg
        if departure_at.tzinfo is None:
            departure_at = departure_at.replace(tzinfo=timezone.utc)
        self.clock = departure_at
        self.cycle_used_min: float = max(0.0, current_cycle_hours) * 60.0
        self.drive_window_min: float = 0.0
        self.duty_window_min: float = 0.0
        self.drive_since_break_min: float = 0.0

        self.segments: list[_Segment] = []
        self.stops: list[_Stop] = []

        self.miles_traveled_total: float = 0.0
        self.miles_since_fuel: float = 0.0

        self.current_label = current_label
        self.pickup_label = pickup_label
        self.dropoff_label = dropoff_label
        self.current_lat = current_lat
        self.current_lon = current_lon
        self.pickup_lat = pickup_lat
        self.pickup_lon = pickup_lon
        self.dropoff_lat = dropoff_lat
        self.dropoff_lon = dropoff_lon

        self.legs: list[_Leg] = [
            _Leg(
                label=current_label,
                end_label=pickup_label,
                distance_miles=leg_to_pickup.distance_miles,
                duration_seconds=leg_to_pickup.duration_seconds,
                polyline=leg_to_pickup.polyline,
                start_lat=current_lat,
                start_lon=current_lon,
                end_lat=pickup_lat,
                end_lon=pickup_lon,
                end_kind="pickup",
            ),
            _Leg(
                label=pickup_label,
                end_label=dropoff_label,
                distance_miles=leg_to_dropoff.distance_miles,
                duration_seconds=leg_to_dropoff.duration_seconds,
                polyline=leg_to_dropoff.polyline,
                start_lat=pickup_lat,
                start_lon=pickup_lon,
                end_lat=dropoff_lat,
                end_lon=dropoff_lon,
                end_kind="dropoff",
            ),
        ]

    def execute(self) -> dict[str, Any]:
        self.stops.append(
            _Stop(
                kind="origin",
                label=f"Start: {self.current_label}",
                arrival=self.clock,
                departure=self.clock,
                lat=self.current_lat,
                lon=self.current_lon,
                distance_from_origin_miles=0.0,
            )
        )

        for leg in self.legs:
            self._drive_leg(leg)
            self._do_terminal_activity(leg)

        return self._compile_output()

    def _drive_leg(self, leg: _Leg) -> None:
        if leg.distance_miles <= 0 or leg.duration_seconds <= 0:
            return

        avg_speed_mph = leg.distance_miles / (leg.duration_seconds / 3600.0)
        # OSRM's car profile can give >70mph averages; cap to a realistic
        # truck-friendly 65 mph so we don't under-plan rest stops.
        avg_speed_mph = max(min(avg_speed_mph, 65.0), 1.0)
        miles_per_minute = avg_speed_mph / 60.0

        miles_remaining = leg.distance_miles

        while miles_remaining > 1e-6:
            drive_cap = self._available_drive_minutes()
            if drive_cap <= 0:
                self._take_rest_or_break()
                continue

            miles_to_fuel = max(self.cfg.fuel_distance_miles - self.miles_since_fuel, 0)
            miles_we_can_do = min(miles_remaining, miles_to_fuel) if miles_to_fuel > 0 else miles_remaining
            if miles_we_can_do <= 0:
                # Defensive: shouldn't really happen because we handle fueling below.
                miles_we_can_do = miles_remaining
            mins_needed = miles_we_can_do / miles_per_minute

            hit_cap = mins_needed > drive_cap
            drive_minutes = drive_cap if hit_cap else mins_needed
            miles_driven = drive_minutes * miles_per_minute

            miles_into_leg_start = leg.distance_miles - miles_remaining
            miles_into_leg_end = miles_into_leg_start + miles_driven
            start_pos = _interpolate_along(leg.polyline, miles_into_leg_start)
            end_pos = _interpolate_along(leg.polyline, miles_into_leg_end)

            self._add_segment(
                _Segment(
                    start=self.clock,
                    end=self.clock + timedelta(minutes=drive_minutes),
                    status="driving",
                    description=f"Drive toward {leg.end_label}",
                    start_lat=start_pos[0],
                    start_lon=start_pos[1],
                    end_lat=end_pos[0],
                    end_lon=end_pos[1],
                    distance_miles=miles_driven,
                )
            )
            self.clock += timedelta(minutes=drive_minutes)
            self.drive_window_min += drive_minutes
            self.duty_window_min += drive_minutes
            self.drive_since_break_min += drive_minutes
            self.cycle_used_min += drive_minutes

            self.miles_traveled_total += miles_driven
            self.miles_since_fuel += miles_driven
            miles_remaining -= miles_driven

            # Fuel stop if we just hit the threshold and still have miles left.
            if self.miles_since_fuel + 1e-6 >= self.cfg.fuel_distance_miles and miles_remaining > 1e-6:
                self._take_fuel_stop(end_pos[0], end_pos[1])

            if hit_cap:
                self._take_rest_or_break()

    def _do_terminal_activity(self, leg: _Leg) -> None:
        dur = (
            self.cfg.pickup_duration_min
            if leg.end_kind == "pickup"
            else self.cfg.dropoff_duration_min
        )
        kind_label = "Pickup" if leg.end_kind == "pickup" else "Drop-off"

        # Make sure we have window + cycle headroom to actually finish this 1-hour
        # task; if not, rest first.
        guard = 0
        while (
            self.cfg.window_limit_min - self.duty_window_min < dur
            or self.cfg.cycle_limit_min - self.cycle_used_min < dur
        ):
            self._take_rest_or_break(force_full_rest=True)
            guard += 1
            if guard > 8:  # cycle + restart should resolve in <=2 iterations; bail otherwise
                break

        self._add_segment(
            _Segment(
                start=self.clock,
                end=self.clock + timedelta(minutes=dur),
                status="on_duty_not_driving",
                description=kind_label,
                start_lat=leg.end_lat,
                start_lon=leg.end_lon,
                end_lat=leg.end_lat,
                end_lon=leg.end_lon,
            )
        )
        self.stops.append(
            _Stop(
                kind=leg.end_kind,
                label=f"{kind_label}: {leg.end_label}",
                arrival=self.clock,
                departure=self.clock + timedelta(minutes=dur),
                lat=leg.end_lat,
                lon=leg.end_lon,
                distance_from_origin_miles=self.miles_traveled_total,
            )
        )
        self.clock += timedelta(minutes=dur)
        self.duty_window_min += dur
        self.cycle_used_min += dur
        # 30+ consecutive minutes of on-duty-not-driving satisfies the
        # 30-minute break-from-driving requirement.
        if dur >= self.cfg.break_duration_min:
            self.drive_since_break_min = 0


    def _available_drive_minutes(self) -> float:
        return min(
            self.cfg.drive_limit_min - self.drive_window_min,
            self.cfg.window_limit_min - self.duty_window_min,
            self.cfg.cycle_limit_min - self.cycle_used_min,
            self.cfg.break_after_min - self.drive_since_break_min,
        )

    def _here(self) -> tuple[float, float]:
        if self.segments:
            last = self.segments[-1]
            lat = last.end_lat if last.end_lat is not None else last.start_lat
            lon = last.end_lon if last.end_lon is not None else last.start_lon
            if lat is not None and lon is not None:
                return lat, lon
        return self.current_lat, self.current_lon

    def _take_rest_or_break(self, *, force_full_rest: bool = False) -> None:
        cfg = self.cfg
        drive_left = cfg.drive_limit_min - self.drive_window_min
        window_left = cfg.window_limit_min - self.duty_window_min
        cycle_left = cfg.cycle_limit_min - self.cycle_used_min
        break_left = cfg.break_after_min - self.drive_since_break_min

        # If cycle is exhausted (or near-exhausted), only a 34-hour restart will
        # free up productive hours.
        if cycle_left < 60:
            self._take_restart()
            return

        # 30-minute break is sufficient when *only* the 8-hour break limit is hit.
        if (
            not force_full_rest
            and break_left <= 0
            and drive_left > cfg.break_duration_min
            and window_left > cfg.break_duration_min
            and cycle_left > cfg.break_duration_min
        ):
            self._take_break()
            return

        self._take_full_rest()

    def _take_break(self) -> None:
        lat, lon = self._here()
        dur = self.cfg.break_duration_min
        self._add_segment(
            _Segment(
                start=self.clock,
                end=self.clock + timedelta(minutes=dur),
                status="off_duty",
                description="30-minute break",
                start_lat=lat,
                start_lon=lon,
                end_lat=lat,
                end_lon=lon,
            )
        )
        self.stops.append(
            _Stop(
                kind="break",
                label="30-minute break",
                arrival=self.clock,
                departure=self.clock + timedelta(minutes=dur),
                lat=lat,
                lon=lon,
                distance_from_origin_miles=self.miles_traveled_total,
            )
        )
        self.clock += timedelta(minutes=dur)
        # The 14-hour window keeps ticking through off-duty time.
        self.duty_window_min += dur
        self.drive_since_break_min = 0

    def _take_full_rest(self) -> None:
        lat, lon = self._here()
        dur = self.cfg.rest_duration_min
        self._add_segment(
            _Segment(
                start=self.clock,
                end=self.clock + timedelta(minutes=dur),
                status="sleeper_berth",
                description="10-hour off-duty rest",
                start_lat=lat,
                start_lon=lon,
                end_lat=lat,
                end_lon=lon,
            )
        )
        self.stops.append(
            _Stop(
                kind="rest",
                label="10-hour rest",
                arrival=self.clock,
                departure=self.clock + timedelta(minutes=dur),
                lat=lat,
                lon=lon,
                distance_from_origin_miles=self.miles_traveled_total,
            )
        )
        self.clock += timedelta(minutes=dur)
        self.drive_window_min = 0
        self.duty_window_min = 0
        self.drive_since_break_min = 0

    def _take_restart(self) -> None:
        lat, lon = self._here()
        dur = self.cfg.restart_duration_min
        self._add_segment(
            _Segment(
                start=self.clock,
                end=self.clock + timedelta(minutes=dur),
                status="off_duty",
                description="34-hour restart (cycle reset)",
                start_lat=lat,
                start_lon=lon,
                end_lat=lat,
                end_lon=lon,
            )
        )
        self.stops.append(
            _Stop(
                kind="restart",
                label="34-hour restart",
                arrival=self.clock,
                departure=self.clock + timedelta(minutes=dur),
                lat=lat,
                lon=lon,
                distance_from_origin_miles=self.miles_traveled_total,
            )
        )
        self.clock += timedelta(minutes=dur)
        self.cycle_used_min = 0
        self.drive_window_min = 0
        self.duty_window_min = 0
        self.drive_since_break_min = 0

    def _take_fuel_stop(self, lat: float, lon: float) -> None:
        dur = self.cfg.fuel_duration_min
        self._add_segment(
            _Segment(
                start=self.clock,
                end=self.clock + timedelta(minutes=dur),
                status="on_duty_not_driving",
                description="Fuel stop",
                start_lat=lat,
                start_lon=lon,
                end_lat=lat,
                end_lon=lon,
            )
        )
        self.stops.append(
            _Stop(
                kind="fuel",
                label="Fuel stop",
                arrival=self.clock,
                departure=self.clock + timedelta(minutes=dur),
                lat=lat,
                lon=lon,
                distance_from_origin_miles=self.miles_traveled_total,
            )
        )
        self.clock += timedelta(minutes=dur)
        self.duty_window_min += dur
        self.cycle_used_min += dur
        # The fuel stop is 30 min of on-duty-not-driving → satisfies the
        # 30-minute break-from-driving rule.
        if dur >= self.cfg.break_duration_min:
            self.drive_since_break_min = 0
        self.miles_since_fuel = 0


    def _add_segment(self, seg: _Segment) -> None:
        # Glue adjacent same-status & same-description segments together.
        if (
            self.segments
            and self.segments[-1].status == seg.status
            and self.segments[-1].end == seg.start
            and self.segments[-1].description == seg.description
        ):
            last = self.segments[-1]
            last.end = seg.end
            last.end_lat = seg.end_lat
            last.end_lon = seg.end_lon
            last.distance_miles += seg.distance_miles
        else:
            self.segments.append(seg)

    def _compile_output(self) -> dict[str, Any]:
        if not self.segments:
            return {
                "segments": [],
                "stops": [],
                "days": [],
                "summary": {
                    "departure_at": self.clock.isoformat(),
                    "arrival_at": self.clock.isoformat(),
                    "total_distance_miles": 0.0,
                    "total_drive_minutes": 0.0,
                    "total_on_duty_not_driving_minutes": 0.0,
                    "total_off_duty_minutes": 0.0,
                    "total_sleeper_berth_minutes": 0.0,
                    "total_trip_minutes": 0.0,
                    "number_of_days": 0,
                    "cycle_hours_used_at_end": self.cycle_used_min / 60.0,
                },
            }

        first_start = self.segments[0].start
        last_end = self.segments[-1].end
        tz = first_start.tzinfo or timezone.utc

        first_day = first_start.date()
        last_day = last_end.date()

        midnight_start = datetime.combine(first_day, time(0, 0, 0), tzinfo=tz)
        midnight_end = datetime.combine(last_day + timedelta(days=1), time(0, 0, 0), tzinfo=tz)

        full_segments: list[_Segment] = []
        if first_start > midnight_start:
            full_segments.append(
                _Segment(
                    start=midnight_start,
                    end=first_start,
                    status="off_duty",
                    description="Pre-trip off-duty",
                    start_lat=self.current_lat,
                    start_lon=self.current_lon,
                    end_lat=self.current_lat,
                    end_lon=self.current_lon,
                )
            )
        full_segments.extend(self.segments)
        if last_end < midnight_end:
            full_segments.append(
                _Segment(
                    start=last_end,
                    end=midnight_end,
                    status="off_duty",
                    description="Post-trip off-duty",
                    start_lat=self.dropoff_lat,
                    start_lon=self.dropoff_lon,
                    end_lat=self.dropoff_lat,
                    end_lon=self.dropoff_lon,
                )
            )

        # Per-day aggregation
        days_by_date: dict[date, dict[str, Any]] = {}
        d = first_day
        while d <= last_day:
            days_by_date[d] = {
                "date": d.isoformat(),
                "entries": [],
                "totals": {
                    "off_duty": 0.0,
                    "sleeper_berth": 0.0,
                    "driving": 0.0,
                    "on_duty_not_driving": 0.0,
                },
                "miles_driven": 0.0,
                "starting_location": "",
                "ending_location": "",
            }
            d += timedelta(days=1)

        for seg in full_segments:
            cursor = seg.start
            while cursor < seg.end:
                day_of = cursor.date()
                next_midnight = datetime.combine(
                    day_of + timedelta(days=1), time(0, 0, 0), tzinfo=cursor.tzinfo
                )
                chunk_end = min(next_midnight, seg.end)
                chunk_min = (chunk_end - cursor).total_seconds() / 60.0
                seg_total_min = seg.duration_minutes or 1e-9
                fraction = chunk_min / seg_total_min
                day_start_dt = datetime.combine(
                    day_of, time(0, 0, 0), tzinfo=cursor.tzinfo
                )
                entry = {
                    "status": seg.status,
                    "status_label": STATUS_LABELS[seg.status],
                    "description": seg.description,
                    "start": cursor.isoformat(),
                    "end": chunk_end.isoformat(),
                    "start_hours": (cursor - day_start_dt).total_seconds() / 3600.0,
                    "end_hours": (chunk_end - day_start_dt).total_seconds() / 3600.0,
                    "duration_minutes": chunk_min,
                    "miles": seg.distance_miles * fraction if seg.status == "driving" else 0.0,
                }
                day_bucket = days_by_date[day_of]
                day_bucket["entries"].append(entry)
                day_bucket["totals"][seg.status] += chunk_min
                if seg.status == "driving":
                    day_bucket["miles_driven"] += entry["miles"]
                cursor = chunk_end

        # Annotate each day's starting/ending location label using the trip's
        # known waypoints — most useful for the FMCSA "From / To" header row.
        location_lookup = [
            (self.current_lat, self.current_lon, self.current_label),
            (self.pickup_lat, self.pickup_lon, self.pickup_label),
            (self.dropoff_lat, self.dropoff_lon, self.dropoff_label),
        ]

        def nearest_label(lat: float | None, lon: float | None) -> str:
            if lat is None or lon is None:
                return ""
            best_label = ""
            best_dist = float("inf")
            for la, lo, lab in location_lookup:
                d = _haversine_miles(lat, lon, la, lo)
                if d < best_dist:
                    best_dist = d
                    best_label = lab
            return best_label

        for d_iso, bucket in days_by_date.items():
            entries = bucket["entries"]
            if not entries:
                continue
            first_seg = full_segments[0]
            last_seg = full_segments[-1]
            # Use the location of the first/last driving or pickup/dropoff for this day.
            day_segs = [s for s in full_segments if s.start.date() <= d_iso <= s.end.date()]
            for seg in day_segs:
                if seg.start.date() == d_iso and (seg.status == "driving" or seg.description in ("Pickup", "Drop-off")):
                    bucket["starting_location"] = nearest_label(seg.start_lat, seg.start_lon)
                    break
            for seg in reversed(day_segs):
                if seg.end.date() == d_iso and (seg.status == "driving" or seg.description in ("Pickup", "Drop-off")):
                    bucket["ending_location"] = nearest_label(seg.end_lat, seg.end_lon)
                    break

        # Round totals nicely for display.
        for bucket in days_by_date.values():
            bucket["totals"] = {k: round(v, 2) for k, v in bucket["totals"].items()}
            bucket["miles_driven"] = round(bucket["miles_driven"], 2)

        days = list(days_by_date.values())

        total_drive = sum(s.duration_minutes for s in self.segments if s.status == "driving")
        total_on_duty_nd = sum(
            s.duration_minutes for s in self.segments if s.status == "on_duty_not_driving"
        )
        total_off = sum(s.duration_minutes for s in self.segments if s.status == "off_duty")
        total_sleep = sum(s.duration_minutes for s in self.segments if s.status == "sleeper_berth")
        total_distance = sum(s.distance_miles for s in self.segments)
        total_trip = (last_end - first_start).total_seconds() / 60.0

        return {
            "segments": [
                {
                    "start": s.start.isoformat(),
                    "end": s.end.isoformat(),
                    "status": s.status,
                    "status_label": STATUS_LABELS[s.status],
                    "description": s.description,
                    "start_lat": s.start_lat,
                    "start_lon": s.start_lon,
                    "end_lat": s.end_lat,
                    "end_lon": s.end_lon,
                    "distance_miles": round(s.distance_miles, 2),
                    "duration_minutes": round(s.duration_minutes, 2),
                }
                for s in self.segments
            ],
            "stops": [
                {
                    "kind": st.kind,
                    "label": st.label,
                    "arrival": st.arrival.isoformat(),
                    "departure": st.departure.isoformat(),
                    "lat": st.lat,
                    "lon": st.lon,
                    "distance_from_origin_miles": round(st.distance_from_origin_miles, 2),
                    "duration_minutes": round((st.departure - st.arrival).total_seconds() / 60.0, 2),
                }
                for st in self.stops
            ],
            "days": days,
            "summary": {
                "departure_at": first_start.isoformat(),
                "arrival_at": last_end.isoformat(),
                "total_distance_miles": round(total_distance, 2),
                "total_drive_minutes": round(total_drive, 2),
                "total_on_duty_not_driving_minutes": round(total_on_duty_nd, 2),
                "total_off_duty_minutes": round(total_off, 2),
                "total_sleeper_berth_minutes": round(total_sleep, 2),
                "total_trip_minutes": round(total_trip, 2),
                "number_of_days": len(days),
                "cycle_hours_used_at_end": round(self.cycle_used_min / 60.0, 2),
            },
        }
