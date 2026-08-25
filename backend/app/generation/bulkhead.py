from __future__ import annotations

import math

import cadquery as cq

from app.generation.common import CircleRadiusSelector
from app.schemas import BulkheadParams


def generate(p: BulkheadParams) -> cq.Workplane:
    result = cq.Workplane("XY").circle(p.diameter / 2).extrude(p.thickness)

    if p.center_hole_diameter is not None:
        result = result.faces(">Z").workplane().hole(p.center_hole_diameter, p.thickness + 1)

    if p.bolt_circle is not None:
        bc = p.bolt_circle
        r = bc.bolt_circle_diameter / 2
        positions = [
            (r * math.cos(2 * math.pi * i / bc.bolt_count), r * math.sin(2 * math.pi * i / bc.bolt_count))
            for i in range(bc.bolt_count)
        ]
        result = (
            result.faces(">Z")
            .workplane()
            .pushPoints(positions)
            .hole(bc.bolt_hole_diameter, p.thickness + 1)
        )

    if p.edge_chamfer > 0:
        result = result.edges(CircleRadiusSelector(p.diameter / 2)).chamfer(p.edge_chamfer)

    return result
