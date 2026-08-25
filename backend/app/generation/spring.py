from __future__ import annotations

import cadquery as cq

from app.schemas import SpringParams


def generate(p: SpringParams) -> cq.Workplane:
    coil_radius = (p.outer_diameter - p.wire_diameter) / 2
    pitch = p.free_length / p.num_coils

    helix = cq.Wire.makeHelix(pitch=pitch, height=p.free_length, radius=coil_radius)
    profile = cq.Workplane("XZ").center(coil_radius, 0).circle(p.wire_diameter / 2)
    return profile.sweep(cq.Workplane(obj=helix), isFrenet=True)
