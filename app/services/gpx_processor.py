import json
import math
from typing import Any

import gpxpy
import gpxpy.gpx


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _estimate_difficulty(dist_km: float, gain_m: float) -> str:
    score = dist_km * 1.0 + gain_m * 0.1
    if score < 10:
        return "easy"
    elif score < 25:
        return "moderate"
    elif score < 50:
        return "hard"
    else:
        return "extreme"


def process_gpx(gpx_content: str) -> dict[str, Any]:
    gpx = gpxpy.parse(gpx_content)

    points: list[tuple[float, float, float | None]] = []  # lat, lon, ele
    for track in gpx.tracks:
        for segment in track.segments:
            for p in segment.points:
                points.append((p.latitude, p.longitude, p.elevation))

    if not points:
        for route in gpx.routes:
            for p in route.points:
                points.append((p.latitude, p.longitude, p.elevation))

    if not points:
        raise ValueError("El archivo GPX no contiene puntos de ruta")

    # Distance + elevation metrics
    total_dist_m = 0.0
    gain_m = 0.0
    loss_m = 0.0
    elevations = [e for _, _, e in points if e is not None]
    max_ele = max(elevations) if elevations else None
    min_ele = min(elevations) if elevations else None

    cumulative: list[tuple[float, float]] = []  # (dist_km, elevation_m)
    for i, (lat, lon, ele) in enumerate(points):
        if i > 0:
            seg_dist = _haversine_m(points[i - 1][0], points[i - 1][1], lat, lon)
            total_dist_m += seg_dist
            prev_ele = points[i - 1][2]
            if ele is not None and prev_ele is not None:
                diff = ele - prev_ele
                if diff > 5:
                    gain_m += diff
                elif diff < -5:
                    loss_m += abs(diff)
        if ele is not None:
            cumulative.append((round(total_dist_m / 1000, 3), round(ele, 1)))

    # Subsample elevation profile to ~300 points max
    profile = cumulative
    if len(profile) > 300:
        step = len(profile) // 300
        profile = profile[::step]

    # Subsample coordinates for Leaflet (~500 points max)
    coords = [(lat, lon) for lat, lon, _ in points]
    if len(coords) > 500:
        step = len(coords) // 500
        coords = coords[::step]
    if coords and coords[-1] != (points[-1][0], points[-1][1]):
        coords.append((points[-1][0], points[-1][1]))

    dist_km = total_dist_m / 1000

    return {
        "total_distance_m": round(total_dist_m, 1),
        "elevation_gain_m": round(gain_m, 1),
        "elevation_loss_m": round(loss_m, 1),
        "max_elevation_m": round(max_ele, 1) if max_ele is not None else None,
        "min_elevation_m": round(min_ele, 1) if min_ele is not None else None,
        "estimated_difficulty": _estimate_difficulty(dist_km, gain_m),
        "elevation_profile": json.dumps(profile),
        "coords": json.dumps(coords),
    }
