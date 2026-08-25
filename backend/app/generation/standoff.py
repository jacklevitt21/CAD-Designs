from __future__ import annotations

import math

import cadquery as cq

from app.schemas import StandoffParams


def generate(p: StandoffParams) -> cq.Workplane:
    if p.body_shape == "round":
        body = cq.Workplane("XY").circle(p.outer_diameter / 2).extrude(p.height)
    else:
        # Regular hexagon, outer_diameter = across-flats (wrench size).
        across_flats = p.outer_diameter
        circumradius = across_flats / (2 * math.cos(math.pi / 6))
        body = cq.Workplane("XY").polygon(6, 2 * circumradius).extrude(p.height)

    if p.through_hole_diameter:
        body = body.faces(">Z").workplane().hole(p.through_hole_diameter, p.height + 1)

    return body
