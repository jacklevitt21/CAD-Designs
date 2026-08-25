from __future__ import annotations

from typing import Callable

import cadquery as cq

from app.generation import enclosure, flange, flat_plate, l_bracket, shaft, standoff
from app.schemas import PartType

GENERATORS: dict[PartType, Callable[..., cq.Workplane]] = {
    PartType.l_bracket: l_bracket.generate,
    PartType.flat_plate: flat_plate.generate,
    PartType.standoff: standoff.generate,
    PartType.flange: flange.generate,
    PartType.enclosure: enclosure.generate,
    PartType.shaft: shaft.generate,
}


def generate_part(part_type: PartType, model) -> cq.Workplane:
    return GENERATORS[part_type](model)
