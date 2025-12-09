import math
from datetime import datetime, time, timezone

EARTH_RADIUS_M = 6371000.0


def haversine_distance_m(lat1, lon1, lat2, lon2):
    """Return distance in meters between two WGS84 coordinates."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_M * c


def parse_iso_datetime(value: str) -> datetime:
    """Parse ISO 8601 date time. Supports trailing 'Z' as UTC."""
    if value is None:
        raise ValueError("start_time is required")
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def extract_time_part_iso(value: str) -> time:
    """Return only time component (HH:MM:SS) from an ISO 8601 datetime string."""
    dt = parse_iso_datetime(value)
    return dt.time().replace(microsecond=0)


def combine_date_and_hms(base_iso: str, hms: str) -> str:
    """Combine the date part of base_iso with an HH:MM:SS string, return ISO 8601 in UTC (Z)."""
    base_dt = parse_iso_datetime(base_iso)
    parts = hms.split(":")
    if len(parts) != 3:
        raise ValueError(f"Invalid time string: {hms}")
    h, m, s = map(int, parts)
    combined = base_dt.replace(hour=h, minute=m, second=s, microsecond=0)
    # Assume time is in UTC already; return with Z suffix
    return combined.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
