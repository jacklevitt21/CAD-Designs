from __future__ import annotations

import cadquery as cq

from app.generation.common import drill_through
from app.schemas import (
    FlatPlateParams,
    HolePatternCorners,
    HolePatternGrid,
    HolePatternLinear,
)


def _hole_xy_positions(p: FlatPlateParams) -> list[tuple[float, float]]:
    hp = p.hole_pattern
    length, width = p.length, p.width

    if isinstance(hp, HolePatternCorners):
        m = hp.edge_margin
        return [
            (m, m),
            (length - m, m),
            (length - m, width - m),
            (m, width - m),
        ]

    if isinstance(hp, HolePatternGrid):
        xs = (
            [length / 2]
            if hp.cols == 1
            else [
                length / 2 - (hp.cols - 1) * hp.spacing_x / 2 + i * hp.spacing_x
                for i in range(hp.cols)
            ]
        )
        ys = (
            [width / 2]
            if hp.rows == 1
            else [
                width / 2 - (hp.rows - 1) * hp.spacing_y / 2 + i * hp.spacing_y
                for i in range(hp.rows)
            ]
        )
        return [(x, y) for y in ys for x in xs]

    if isinstance(hp, HolePatternLinear):
        n = hp.hole_count
        offsets = [0.0] if n == 1 else [-(n - 1) * hp.spacing / 2 + i * hp.spacing for i in range(n)]
        if hp.orientation == "x":
            return [(length / 2 + off, width / 2) for off in offsets]
        return [(length / 2, width / 2 + off) for off in offsets]

    raise ValueError(f"Unsupported hole_pattern: {hp}")


def generate(p: FlatPlateParams) -> cq.Workplane:
    result = cq.Workplane("XY").box(
        p.length, p.width, p.thickness, centered=(False, False, False)
    )

    for x, y in _hole_xy_positions(p):
        result = drill_through(result, (x, y, 0), (0, 0, 1), p.hole_diameter, p.thickness)

    if p.corner_fillet_radius > 0:
        result = result.edges("|Z").fillet(p.corner_fillet_radius)

    return result
