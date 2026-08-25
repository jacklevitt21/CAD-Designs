from __future__ import annotations

import cadquery as cq

from app.generation.common import drill_through
from app.schemas import EnclosureParams


def generate(p: EnclosureParams) -> cq.Workplane:
    outer = cq.Workplane("XY").box(
        p.length, p.width, p.height, centered=(False, False, False)
    )

    if p.corner_fillet_radius > 0:
        outer = outer.edges("|Z").fillet(p.corner_fillet_radius)

    # Open-top box: hollow out everything except the base (wall_thickness)
    # and the side walls (wall_thickness), leaving the top open.
    t = p.wall_thickness
    cavity = (
        cq.Workplane("XY")
        .workplane(offset=t)
        .box(
            p.length - 2 * t,
            p.width - 2 * t,
            p.height,  # taller than needed so it cuts clean through the top
            centered=(False, False, False),
        )
        .translate((t, t, 0))
    )
    result = outer.cut(cavity)

    if p.mounting_holes is not None:
        mh = p.mounting_holes
        m = mh.inset
        corners = [
            (m, m),
            (p.length - m, m),
            (p.length - m, p.width - m),
            (m, p.width - m),
        ]
        for x, y in corners:
            result = drill_through(result, (x, y, 0), (0, 0, 1), mh.hole_diameter, t)

    return result
