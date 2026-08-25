"""Shared CadQuery helpers used by every part generator."""
from __future__ import annotations

import cadquery as cq

Vec = tuple[float, float, float]


def drill_through(
    solid: cq.Workplane,
    start_point: Vec,
    axis: Vec,
    diameter: float,
    depth: float,
    margin: float = 5.0,
) -> cq.Workplane:
    """Cut a round hole of `diameter` starting at `start_point`, travelling
    along `axis` for `depth` (the material thickness at that point).

    The cutter is extended `margin` beyond both ends so it fully pierces the
    solid regardless of small face/position inaccuracies.
    """
    ax, ay, az = axis
    origin = (start_point[0] - ax * margin, start_point[1] - ay * margin, start_point[2] - az * margin)
    plane = cq.Plane(origin=origin, normal=axis)
    cutter = cq.Workplane(plane).circle(diameter / 2).extrude(depth + 2 * margin)
    return solid.cut(cutter)


def evenly_spaced(count: int, low: float, high: float) -> list[float]:
    """`count` positions spread between low and high inclusive.
    count=1 -> midpoint. count>=2 -> low..high evenly spaced.
    """
    if count <= 1:
        return [(low + high) / 2]
    step = (high - low) / (count - 1)
    return [low + i * step for i in range(count)]


class CircleRadiusSelector(cq.Selector):
    """Selects circular edges whose radius matches within a tolerance.
    Useful for filleting/chamfering just the outer rim of a disc-like part
    without touching bores, bolt holes, or a hub.
    """

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
