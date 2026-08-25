from __future__ import annotations

import cadquery as cq

from app.generation.common import drill_through, evenly_spaced
from app.schemas import LBracketParams


def generate(p: LBracketParams) -> cq.Workplane:
    t = p.thickness
    w = p.width

    leg1 = cq.Workplane("XY").box(
        p.leg1_length, t, w, centered=(False, False, False)
    )
    leg2 = cq.Workplane("XY").box(
        t, p.leg2_length, w, centered=(False, False, False)
    )
    result = leg1.union(leg2)

    # Holes on leg1: drilled along +Y (through the material thickness),
    # positioned near the free end (X = leg1_length), spread across width Z.
    z_positions = evenly_spaced(p.holes_per_leg, p.edge_margin, w - p.edge_margin)
    for z in z_positions:
        x = p.leg1_length - p.edge_margin
        result = drill_through(result, (x, 0, z), (0, 1, 0), p.hole_diameter, t)

    # Holes on leg2: drilled along +X, positioned near the free end (Y = leg2_length).
    for z in z_positions:
        y = p.leg2_length - p.edge_margin
        result = drill_through(result, (0, y, z), (1, 0, 0), p.hole_diameter, t)

    if p.inner_fillet_radius > 0:
        inner_edge = result.edges(
            cq.selectors.NearestToPointSelector((t, t, w / 2))
        )
        result = inner_edge.fillet(p.inner_fillet_radius)

    if p.edge_fillet_radius > 0:
        result = result.edges("|Z").fillet(p.edge_fillet_radius)

    return result
