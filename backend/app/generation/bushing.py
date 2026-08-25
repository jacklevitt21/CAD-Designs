from __future__ import annotations

import cadquery as cq

from app.schemas import BushingParams


def generate(p: BushingParams) -> cq.Workplane:
    body = cq.Workplane("XY").circle(p.outer_diameter / 2).extrude(p.length)

    if p.flange is not None:
        flange = (
            cq.Workplane("XY")
            .workplane(offset=p.length)
            .circle(p.flange.diameter / 2)
            .extrude(p.flange.thickness)
        )
        body = body.union(flange)

    total_height = p.length + (p.flange.thickness if p.flange else 0)
    body = body.faces("<Z").workplane().hole(p.inner_diameter, total_height + 1)

    return body
