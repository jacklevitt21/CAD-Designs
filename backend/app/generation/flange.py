from __future__ import annotations

import math

import cadquery as cq

from app.schemas import FlangeParams


class _CircleRadiusSelector(cq.Selector):
    """Selects circular edges whose radius matches within a tolerance."""

    def __init__(self, radius: float, tol: float = 1e-3):
        self.radius = radius
        self.tol = tol

    def filter(self, objectList):
        matches = []
        for edge in objectList:
            if edge.geomType() != "CIRCLE":
                continue
            try:
                if abs(edge.radius() - self.radius) < self.tol:
                    matches.append(edge)
            except Exception:
                continue
        return matches


def generate(p: FlangeParams) -> cq.Workplane:
    result = (
        cq.Workplane("XY")
        .circle(p.outer_diameter / 2)
        .extrude(p.thickness)
    )

    if p.hub is not None:
        hub = (
            cq.Workplane("XY")
            .workplane(offset=p.thickness)
            .circle(p.hub.diameter / 2)
            .extrude(p.hub.height)
        )
        result = result.union(hub)

    total_height = p.thickness + (p.hub.height if p.hub else 0)

    # Center bore, straight through everything.
    result = (
        result.faces("<Z")
        .workplane()
        .hole(p.bore_diameter, total_height + 1)
    )

    # Bolt circle holes, evenly spaced, through the base thickness only.
    bolt_positions = []
    r = p.bolt_circle_diameter / 2
    for i in range(p.bolt_count):
        angle = 2 * math.pi * i / p.bolt_count
        bolt_positions.append((r * math.cos(angle), r * math.sin(angle)))

    result = (
        result.faces("<Z")
        .workplane()
        .pushPoints(bolt_positions)
        .hole(p.bolt_hole_diameter, p.thickness + 1)
    )

    if p.fillet_radius > 0:
        # Round the outer rim edges only (top & bottom of the base disc at
        # outer_diameter) — leaves the bore, bolt holes, and hub untouched.
        result = result.edges(_CircleRadiusSelector(p.outer_diameter / 2)).fillet(
            p.fillet_radius
        )

    return result
