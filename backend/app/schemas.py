"""Parameter schemas for every supported part category.

Each category has a Pydantic model describing its *fully resolved* parameters
(everything required to generate geometry — defaults already filled in).
`DEFAULTS` holds the default value for every optional field per category, and
is also the source of truth for which top-level keys are "fillable" when the
LLM parsing layer omits them (see app/parsing.py and app/resolve.py).
"""
from __future__ import annotations

from enum import Enum
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field


class PartType(str, Enum):
    l_bracket = "l_bracket"
    flat_plate = "flat_plate"
    standoff = "standoff"
    flange = "flange"
    enclosure = "enclosure"
    shaft = "shaft"
    spring = "spring"
    gear = "gear"
    channel = "channel"
    bushing = "bushing"
    bulkhead = "bulkhead"


# --------------------------------------------------------------------------
# Shared sub-schemas
# --------------------------------------------------------------------------

class HolePatternCorners(BaseModel):
    type: Literal["corners"] = "corners"
    edge_margin: float = Field(..., description="Distance from hole center to nearest edges (mm)")


class HolePatternGrid(BaseModel):
    type: Literal["grid"] = "grid"
    rows: int = Field(..., ge=1)
    cols: int = Field(..., ge=1)
    spacing_x: float = Field(..., gt=0)
    spacing_y: float = Field(..., gt=0)
    edge_margin: float = Field(..., gt=0)


class HolePatternLinear(BaseModel):
    type: Literal["linear"] = "linear"
    hole_count: int = Field(..., ge=1)
    spacing: float = Field(..., gt=0)
    edge_margin: float = Field(..., gt=0)
    orientation: Literal["x", "y"] = "x"


HolePattern = Union[HolePatternCorners, HolePatternGrid, HolePatternLinear]


class Chamfer(BaseModel):
    size: float = Field(..., gt=0, description="Chamfer leg length (mm)")
    angle_deg: float = Field(45.0, gt=0, lt=90)


class Hub(BaseModel):
    diameter: float = Field(..., gt=0)
    height: float = Field(..., gt=0)


class ShaftSegment(BaseModel):
    diameter: float = Field(..., gt=0)
    length: float = Field(..., gt=0)


class MountingHoles(BaseModel):
    hole_diameter: float = Field(..., gt=0)
    inset: float = Field(..., gt=0, description="Distance from each corner to the hole center (mm)")


class BushingFlange(BaseModel):
    diameter: float = Field(..., gt=0)
    thickness: float = Field(..., gt=0)


class BoltCircle(BaseModel):
    bolt_circle_diameter: float = Field(..., gt=0)
    bolt_count: int = Field(..., ge=2, le=24)
    bolt_hole_diameter: float = Field(..., gt=0)


# --------------------------------------------------------------------------
# Category parameter schemas (fully resolved — no None/optional business
# logic left; that lives in DEFAULTS + resolve.py)
# --------------------------------------------------------------------------

class LBracketParams(BaseModel):
    leg1_length: float = Field(..., gt=0)
    leg2_length: float = Field(..., gt=0)
    width: float = Field(..., gt=0)
    thickness: float = Field(..., gt=0)
    inner_fillet_radius: float = Field(0, ge=0)
    edge_fillet_radius: float = Field(0, ge=0)
    hole_diameter: float = Field(..., gt=0)
    holes_per_leg: int = Field(1, ge=1, le=4)
    edge_margin: float = Field(..., gt=0)


class FlatPlateParams(BaseModel):
    length: float = Field(..., gt=0)
    width: float = Field(..., gt=0)
    thickness: float = Field(..., gt=0)
    corner_fillet_radius: float = Field(0, ge=0)
    hole_diameter: float = Field(..., gt=0)
    hole_pattern: HolePattern = Field(default_factory=lambda: HolePatternCorners(edge_margin=8))


class StandoffParams(BaseModel):
    body_shape: Literal["round", "hex"] = "round"
    outer_diameter: float = Field(..., gt=0)
    height: float = Field(..., gt=0)
    through_hole_diameter: Optional[float] = Field(None, gt=0)


class FlangeParams(BaseModel):
    outer_diameter: float = Field(..., gt=0)
    thickness: float = Field(..., gt=0)
    bore_diameter: float = Field(..., gt=0)
    bolt_circle_diameter: float = Field(..., gt=0)
    bolt_count: int = Field(..., ge=2, le=24)
    bolt_hole_diameter: float = Field(..., gt=0)
    fillet_radius: float = Field(0, ge=0)
    hub: Optional[Hub] = None


class EnclosureParams(BaseModel):
    length: float = Field(..., gt=0)
    width: float = Field(..., gt=0)
    height: float = Field(..., gt=0)
    wall_thickness: float = Field(..., gt=0)
    corner_fillet_radius: float = Field(0, ge=0)
    mounting_holes: Optional[MountingHoles] = None


class ShaftParams(BaseModel):
    segments: list[ShaftSegment] = Field(..., min_length=1)
    fillet_between_steps: float = Field(0, ge=0)
    start_chamfer: Optional[Chamfer] = None
    end_chamfer: Optional[Chamfer] = None


class SpringParams(BaseModel):
    wire_diameter: float = Field(..., gt=0)
    outer_diameter: float = Field(..., gt=0)
    free_length: float = Field(..., gt=0)
    num_coils: float = Field(..., gt=0)


class GearParams(BaseModel):
    num_teeth: int = Field(..., ge=6, le=200)
    module: float = Field(..., gt=0, description="Standard gear module (mm) — tooth size; pitch_diameter = module * num_teeth")
    thickness: float = Field(..., gt=0)
    bore_diameter: float = Field(..., gt=0)
    pressure_angle_deg: float = Field(20.0, gt=0, lt=45)


class ChannelParams(BaseModel):
    length: float = Field(..., gt=0, description="Extrusion length of the channel")
    web_width: float = Field(..., gt=0, description="Overall outer width across the two flanges")
    flange_height: float = Field(..., gt=0)
    thickness: float = Field(..., gt=0)
    inner_fillet_radius: float = Field(0, ge=0)
    hole_diameter: float = Field(..., gt=0)
    holes_per_flange: int = Field(1, ge=1, le=4)
    edge_margin: float = Field(..., gt=0)


class BushingParams(BaseModel):
    inner_diameter: float = Field(..., gt=0)
    outer_diameter: float = Field(..., gt=0)
    length: float = Field(..., gt=0)
    flange: Optional[BushingFlange] = None


class BulkheadParams(BaseModel):
    diameter: float = Field(..., gt=0, description="Outer diameter, sized to fit inside the body tube")
    thickness: float = Field(..., gt=0)
    center_hole_diameter: Optional[float] = Field(None, gt=0, description="Attachment hole (e.g. eye bolt / U-bolt), not a bore")
    edge_chamfer: float = Field(0, ge=0, description="Chamfer on the outer rim to ease sliding into a tube")
    bolt_circle: Optional[BoltCircle] = None


PARAM_MODELS: dict[PartType, type[BaseModel]] = {
    PartType.l_bracket: LBracketParams,
    PartType.flat_plate: FlatPlateParams,
    PartType.standoff: StandoffParams,
    PartType.flange: FlangeParams,
    PartType.enclosure: EnclosureParams,
    PartType.shaft: ShaftParams,
    PartType.spring: SpringParams,
    PartType.gear: GearParams,
    PartType.channel: ChannelParams,
    PartType.bushing: BushingParams,
    PartType.bulkhead: BulkheadParams,
}


# --------------------------------------------------------------------------
# Defaults — every field NOT in a category's required-with-no-default set
# has a documented default here. Keys mirror the Pydantic model fields.
# --------------------------------------------------------------------------

DEFAULTS: dict[PartType, dict] = {
    PartType.l_bracket: {
        "leg1_length": 60.0,
        "leg2_length": 40.0,
        "width": 30.0,
        "thickness": 5.0,
        "inner_fillet_radius": 0.0,
        "edge_fillet_radius": 0.0,
        "hole_diameter": 6.0,
        "holes_per_leg": 1,
        "edge_margin": 8.0,
    },
    PartType.flat_plate: {
        "length": 80.0,
        "width": 60.0,
        "thickness": 5.0,
        "corner_fillet_radius": 0.0,
        "hole_diameter": 6.0,
        "hole_pattern": {"type": "corners", "edge_margin": 8.0},
    },
    PartType.standoff: {
        "body_shape": "round",
        "outer_diameter": 10.0,
        "height": 20.0,
        "through_hole_diameter": 4.0,
    },
    PartType.flange: {
        "outer_diameter": 80.0,
        "thickness": 8.0,
        "bore_diameter": 25.0,
        "bolt_circle_diameter": 60.0,
        "bolt_count": 6,
        "bolt_hole_diameter": 6.0,
        "fillet_radius": 0.0,
        "hub": None,
    },
    PartType.enclosure: {
        "length": 100.0,
        "width": 80.0,
        "height": 40.0,
        "wall_thickness": 3.0,
        "corner_fillet_radius": 2.0,
        "mounting_holes": {"hole_diameter": 4.0, "inset": 8.0},
    },
    PartType.shaft: {
        "segments": [{"diameter": 10.0, "length": 50.0}],
        "fillet_between_steps": 0.0,
        "start_chamfer": None,
        "end_chamfer": None,
    },
    PartType.spring: {
        "wire_diameter": 2.0,
        "outer_diameter": 20.0,
        "free_length": 40.0,
        "num_coils": 8.0,
    },
    PartType.gear: {
        "num_teeth": 20,
        "module": 2.0,
        "thickness": 8.0,
        "bore_diameter": 6.0,
        "pressure_angle_deg": 20.0,
    },
    PartType.channel: {
        "length": 60.0,
        "web_width": 30.0,
        "flange_height": 20.0,
        "thickness": 3.0,
        "inner_fillet_radius": 0.0,
        "hole_diameter": 6.0,
        "holes_per_flange": 1,
        "edge_margin": 8.0,
    },
    PartType.bushing: {
        "inner_diameter": 8.0,
        "outer_diameter": 14.0,
        "length": 20.0,
        "flange": None,
    },
    PartType.bulkhead: {
        "diameter": 60.0,
        "thickness": 6.0,
        "center_hole_diameter": 8.0,
        "edge_chamfer": 1.0,
        "bolt_circle": None,
    },
}


# --------------------------------------------------------------------------
# API request/response envelopes
# --------------------------------------------------------------------------

class GenerateTextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class RegenerateRequest(BaseModel):
    part_type: PartType
    name: Optional[str] = None
    material: Optional[str] = None
    parameters: dict


class PartResponse(BaseModel):
    part_id: str
    part_type: PartType
    name: Optional[str]
    material: Optional[str]
    parameters: dict
    defaulted_fields: list[str]
    warnings: list[str] = []
    step_url: str
    stl_url: str
