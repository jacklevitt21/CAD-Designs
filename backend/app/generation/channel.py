from __future__ import annotations

import cadquery as cq

from app.generation.common import drill_through, evenly_spaced
from app.schemas import ChannelParams


def generate(p: ChannelParams) -> cq.Workplane:
    t = p.thickness
    w = p.web_width
    h = p.flange_height
    length = p.length

    web = cq.Workplane("XY").box(w, t, length, centered=(False, False, False))
    left_flange = cq.Workplane("XY").box(t, h, length, centered=(False, False, False))
    right_flange = cq.Workplane("XY").box(t, h, length, centered=(False, False, False)).translate((w - t, 0, 0))
    result = web.union(left_flange).union(right_flange)

    z_positions = evenly_spaced(p.holes_per_flange, p.edge_margin, length - p.edge_margin)
    hole_y = h - p.edge_margin

    for z in z_positions:
        # Left flange: outer face at X=0, drilled along +X.
        result = drill_through(result, (0, hole_y, z), (1, 0, 0), p.hole_diameter, t)
        # Right flange: outer face at X=w, drilled along -X.
        result = drill_through(result, (w, hole_y, z), (-1, 0, 0), p.hole_diameter, t)

    if p.inner_fillet_radius > 0:
        for corner in [(t, t, length / 2), (w - t, t, length / 2)]:
            result = result.edges(cq.selectors.NearestToPointSelector(corner)).fillet(
                p.inner_fillet_radius
            )

    return result
