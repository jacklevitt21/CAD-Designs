"""Spur gear with a real involute tooth profile (standard full-depth, 1.0
addendum / 1.25 dedendum), built by tracing the involute curve of the base
circle for each tooth flank and patterning it around the gear.

This is a visual/geometric approximation suitable for a portfolio piece —
it is not checked against AGMA/ISO tolerancing and doesn't model backlash,
undercut correction for very low tooth counts, etc.
"""
from __future__ import annotations

import math

import cadquery as cq

from app.schemas import GearParams


def _involute_xy(base_radius: float, t: float) -> tuple[float, float]:
    x = base_radius * (math.cos(t) + t * math.sin(t))
    y = base_radius * (math.sin(t) - t * math.cos(t))
    return x, y


def pitch_radius(num_teeth: int, module: float) -> float:
    return module * num_teeth / 2


def base_radius(num_teeth: int, module: float, pressure_angle_deg: float) -> float:
    return pitch_radius(num_teeth, module) * math.cos(math.radians(pressure_angle_deg))


def addendum_radius(num_teeth: int, module: float) -> float:
    return pitch_radius(num_teeth, module) + module


def root_radius(num_teeth: int, module: float, pressure_angle_deg: float) -> float:
    dedendum_r = pitch_radius(num_teeth, module) - 1.25 * module
    br = base_radius(num_teeth, module, pressure_angle_deg)
    # Never let the root fall meaningfully below the base circle — that
    # region isn't traced by the involute construction used here.
    return max(dedendum_r, br * 0.9)


def _profile_points(p: GearParams, points_per_flank: int = 6) -> list[tuple[float, float]]:
    pa = math.radians(p.pressure_angle_deg)
    pr = pitch_radius(p.num_teeth, p.module)
    br = base_radius(p.num_teeth, p.module, p.pressure_angle_deg)
    ar = addendum_radius(p.num_teeth, p.module)
    rr = root_radius(p.num_teeth, p.module, p.pressure_angle_deg)

    inv_pa = math.tan(pa) - pa
    half_tooth_ang = math.pi / (2 * p.num_teeth) + inv_pa

    t_pitch = math.sqrt(max((pr / br) ** 2 - 1, 0))
    t_addendum = math.sqrt(max((ar / br) ** 2 - 1, 0))
    px, py = _involute_xy(br, t_pitch)
    phi_pitch = math.atan2(py, px)

    start_r = max(rr, br)
    t_start = math.sqrt(max((start_r / br) ** 2 - 1, 0))

    tooth_pitch_ang = 2 * math.pi / p.num_teeth
    points: list[tuple[float, float]] = []

    for i in range(p.num_teeth):
        center = i * tooth_pitch_ang

        # Small root-circle point leading into the right flank.
        points.append(
            (
                rr * math.cos(center - tooth_pitch_ang / 2 + 0.01),
                rr * math.sin(center - tooth_pitch_ang / 2 + 0.01),
            )
        )

        right_offset = (center - half_tooth_ang) - phi_pitch
        for j in range(points_per_flank + 1):
            t = t_start + (t_addendum - t_start) * j / points_per_flank
            x, y = _involute_xy(br, t)
            ang = math.atan2(y, x) + right_offset
            r = math.hypot(x, y)
            points.append((r * math.cos(ang), r * math.sin(ang)))

        left_offset = (center + half_tooth_ang) + phi_pitch
        for j in range(points_per_flank, -1, -1):
            t = t_start + (t_addendum - t_start) * j / points_per_flank
            x, y = _involute_xy(br, t)
            ang = -math.atan2(y, x) + left_offset
            r = math.hypot(x, y)
            points.append((r * math.cos(ang), r * math.sin(ang)))

    return points


def generate(p: GearParams) -> cq.Workplane:
    points = _profile_points(p)
    result = cq.Workplane("XY").polyline(points).close().extrude(p.thickness)
    result = result.faces(">Z").workplane().hole(p.bore_diameter, p.thickness + 1)
    return result
