from __future__ import annotations

import cadquery as cq

from app.schemas import ShaftParams


def generate(p: ShaftParams) -> cq.Workplane:
    result = None
    z = 0.0
    for seg in p.segments:
        piece = (
            cq.Workplane("XY")
            .workplane(offset=z)
            .circle(seg.diameter / 2)
            .extrude(seg.length)
        )
        result = piece if result is None else result.union(piece)
        z += seg.length

    if p.fillet_between_steps > 0 and len(p.segments) > 1:
        # Fillet the internal step edges (circles at each segment boundary,
        # excluding the two shaft ends).
        boundary_z = 0.0
        boundary_radii = []
        for seg in p.segments[:-1]:
            boundary_z += seg.length
            boundary_radii.append(seg.diameter / 2)
        for r in set(boundary_radii):
            result = result.edges(_CircleAtRadiusNotEnds(r, 0.0, z)).fillet(
                p.fillet_between_steps
            )

    if p.start_chamfer is not None:
        result = result.faces("<Z").chamfer(p.start_chamfer.size)

    if p.end_chamfer is not None:
        result = result.faces(">Z").chamfer(p.end_chamfer.size)

    return result


class _CircleAtRadiusNotEnds(cq.Selector):
    """Circular edges at a given radius, excluding the shaft's two end faces
    (z == z_min or z == z_max)."""

    def __init__(self, radius: float, z_min: float, z_max: float, tol: float = 1e-3):
        self.radius = radius
        self.z_min = z_min
        self.z_max = z_max
        self.tol = tol

    def filter(self, objectList):
        matches = []
        for edge in objectList:
            if edge.geomType() != "CIRCLE":
                continue
            try:
                if abs(edge.radius() - self.radius) >= self.tol:
                    continue
            except Exception:
                continue
            z = edge.Center().z
            if abs(z - self.z_min) < self.tol or abs(z - self.z_max) < self.tol:
                continue
            matches.append(edge)
        return matches
