from __future__ import annotations

from typing import Callable

import cadquery as cq

from app.generation import (
    bulkhead,
    bushing,
    channel,
    enclosure,
    flange,
    flat_plate,
    gear,
    l_bracket,
    shaft,
    spring,
    standoff,
)
from app.schemas import PartType

GENERATORS: dict[PartType, Callable[..., cq.Workplane]] = {
    PartType.l_bracket: l_bracket.generate,
    PartType.flat_plate: flat_plate.generate,
    PartType.standoff: standoff.generate,
    PartType.flange: flange.generate,
    PartType.enclosure: enclosure.generate,
    PartType.shaft: shaft.generate,
    PartType.spring: spring.generate,
    PartType.gear: gear.generate,
    PartType.channel: channel.generate,
    PartType.bushing: bushing.generate,
    PartType.bulkhead: bulkhead.generate,
}


def generate_part(part_type: PartType, model) -> cq.Workplane:
    return GENERATORS[part_type](model)
