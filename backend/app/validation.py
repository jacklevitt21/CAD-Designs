"""Cross-field geometric validation beyond what Pydantic's field constraints
(gt=0, etc.) can express — e.g. "hole diameter must fit within the part".

Each function takes a fully-resolved, Pydantic-typed params model and returns
a list of human-readable error strings (empty list = valid).
"""
from __future__ import annotations

from app.generation.gear import base_radius, root_radius
from app.resolve import PartValidationError
from app.schemas import (
    BulkheadParams,
    BushingParams,
    ChannelParams,
    EnclosureParams,
    FlangeParams,
    FlatPlateParams,
    GearParams,
    HolePatternCorners,
    HolePatternGrid,
    HolePatternLinear,
    LBracketParams,
    PartType,
    ShaftParams,
    SpringParams,
    StandoffParams,
)


def validate_l_bracket(p: LBracketParams) -> list[str]:
    errors = []
    if p.hole_diameter >= p.thickness * 4:
        errors.append(
            f"hole_diameter ({p.hole_diameter}mm) is too large relative to thickness ({p.thickness}mm)"
        )
    min_leg = min(p.leg1_length, p.leg2_length)
    if p.edge_margin * 2 >= min_leg:
        errors.append(
            f"edge_margin ({p.edge_margin}mm) leaves no room on the shorter leg ({min_leg}mm)"
        )
    if p.hole_diameter / 2 >= p.edge_margin:
        errors.append(
            f"hole_diameter ({p.hole_diameter}mm) is too large for edge_margin ({p.edge_margin}mm) — hole would breach the edge"
        )
    if p.inner_fillet_radius >= min(p.leg1_length, p.leg2_length, p.width):
        errors.append("inner_fillet_radius is too large for the bracket's legs")
    if p.edge_fillet_radius * 2 >= p.width:
        errors.append("edge_fillet_radius is too large relative to width")
    return errors


def validate_flat_plate(p: FlatPlateParams) -> list[str]:
    errors = []
    if p.hole_diameter / 2 >= min(p.length, p.width) / 2:
        errors.append(
            f"hole_diameter ({p.hole_diameter}mm) is too large for the plate ({p.length}x{p.width}mm)"
        )
    hp = p.hole_pattern
    if isinstance(hp, HolePatternCorners):
        if hp.edge_margin * 2 >= min(p.length, p.width):
            errors.append("hole_pattern.edge_margin is too large for the plate size")
        if p.hole_diameter / 2 >= hp.edge_margin:
            errors.append("hole_diameter is too large for hole_pattern.edge_margin — hole would breach the edge")
    elif isinstance(hp, HolePatternGrid):
        span_x = (hp.cols - 1) * hp.spacing_x + 2 * hp.edge_margin
        span_y = (hp.rows - 1) * hp.spacing_y + 2 * hp.edge_margin
        if span_x > p.length or span_y > p.width:
            errors.append(
                f"grid hole pattern ({span_x:.1f}x{span_y:.1f}mm footprint) doesn't fit on the plate ({p.length}x{p.width}mm)"
            )
    elif isinstance(hp, HolePatternLinear):
        span = (hp.hole_count - 1) * hp.spacing + 2 * hp.edge_margin
        limit = p.length if hp.orientation == "x" else p.width
        if span > limit:
            errors.append(f"linear hole pattern ({span:.1f}mm) doesn't fit along the plate's {hp.orientation}-axis ({limit}mm)")
    if p.corner_fillet_radius * 2 >= min(p.length, p.width):
        errors.append("corner_fillet_radius is too large relative to the plate size")
    return errors


def validate_standoff(p: StandoffParams) -> list[str]:
    errors = []
    if p.through_hole_diameter is not None and p.through_hole_diameter >= p.outer_diameter * 0.9:
        errors.append(
            f"through_hole_diameter ({p.through_hole_diameter}mm) is too large for outer_diameter ({p.outer_diameter}mm)"
        )
    return errors


def validate_flange(p: FlangeParams) -> list[str]:
    errors = []
    if p.bore_diameter >= p.bolt_circle_diameter:
        errors.append("bore_diameter must be smaller than bolt_circle_diameter")
    if p.bolt_circle_diameter + p.bolt_hole_diameter >= p.outer_diameter:
        errors.append("bolt_circle_diameter + bolt_hole_diameter must be smaller than outer_diameter")
    if p.hub is not None and p.hub.diameter <= p.bore_diameter:
        errors.append("hub.diameter must be larger than bore_diameter")
    return errors


def validate_enclosure(p: EnclosureParams) -> list[str]:
    errors = []
    if p.wall_thickness * 2 >= min(p.length, p.width):
        errors.append(
            f"wall_thickness ({p.wall_thickness}mm) is too large for the enclosure footprint ({p.length}x{p.width}mm)"
        )
    if p.corner_fillet_radius * 2 >= min(p.length, p.width):
        errors.append("corner_fillet_radius is too large relative to the footprint")
    if p.mounting_holes is not None:
        mh = p.mounting_holes
        if mh.inset * 2 >= min(p.length, p.width):
            errors.append("mounting_holes.inset is too large for the footprint")
        if mh.hole_diameter / 2 >= mh.inset:
            errors.append("mounting_holes.hole_diameter is too large for the inset — hole would breach the edge")
    return errors


def validate_shaft(p: ShaftParams) -> list[str]:
    errors = []
    max_d = max(s.diameter for s in p.segments)
    min_d = min(s.diameter for s in p.segments)
    if p.fillet_between_steps > 0 and p.fillet_between_steps >= min_d / 2:
        errors.append("fillet_between_steps is too large relative to the narrowest segment")
    shortest_len = min(s.length for s in p.segments)
    if p.start_chamfer is not None and p.start_chamfer.size >= min_d / 2:
        errors.append("start_chamfer.size is too large relative to the shaft diameter")
    if p.end_chamfer is not None and p.end_chamfer.size >= min_d / 2:
        errors.append("end_chamfer.size is too large relative to the shaft diameter")
    if p.start_chamfer is not None and p.start_chamfer.size >= shortest_len:
        errors.append("start_chamfer.size is too large relative to a segment length")
    return errors


def validate_spring(p: SpringParams) -> list[str]:
    errors = []
    if p.wire_diameter >= p.outer_diameter:
        errors.append(f"wire_diameter ({p.wire_diameter}mm) must be smaller than outer_diameter ({p.outer_diameter}mm)")
        return errors
    pitch = p.free_length / p.num_coils
    if pitch < p.wire_diameter * 1.02:
        errors.append(
            f"free_length is too short for {p.num_coils} coils of {p.wire_diameter}mm wire — coils would overlap"
        )
    return errors


def validate_gear(p: GearParams) -> list[str]:
    errors = []
    rr = root_radius(p.num_teeth, p.module, p.pressure_angle_deg)
    br = base_radius(p.num_teeth, p.module, p.pressure_angle_deg)
    if p.bore_diameter / 2 >= min(rr, br) * 0.85:
        errors.append(
            f"bore_diameter ({p.bore_diameter}mm) is too large for {p.num_teeth} teeth at module {p.module} — it would cut into the teeth"
        )
    return errors


def validate_channel(p: ChannelParams) -> list[str]:
    errors = []
    if p.hole_diameter >= p.thickness * 4:
        errors.append(f"hole_diameter ({p.hole_diameter}mm) is too large relative to thickness ({p.thickness}mm)")
    if p.edge_margin * 2 >= p.length:
        errors.append(f"edge_margin ({p.edge_margin}mm) leaves no room along the channel's length ({p.length}mm)")
    if p.hole_diameter / 2 >= p.edge_margin:
        errors.append(f"hole_diameter ({p.hole_diameter}mm) is too large for edge_margin ({p.edge_margin}mm)")
    if p.hole_diameter / 2 >= p.flange_height - p.edge_margin:
        errors.append("hole_diameter is too large for the flange_height — hole would breach the top edge")
    if p.inner_fillet_radius >= min(p.web_width, p.flange_height, p.thickness * 4):
        errors.append("inner_fillet_radius is too large for the channel's geometry")
    if p.thickness * 2 >= p.web_width:
        errors.append(f"thickness ({p.thickness}mm) is too large relative to web_width ({p.web_width}mm)")
    return errors


def validate_bushing(p: BushingParams) -> list[str]:
    errors = []
    if p.inner_diameter >= p.outer_diameter * 0.95:
        errors.append(
            f"inner_diameter ({p.inner_diameter}mm) is too large for outer_diameter ({p.outer_diameter}mm) — wall too thin"
        )
    if p.flange is not None and p.flange.diameter <= p.outer_diameter:
        errors.append("flange.diameter must be larger than outer_diameter to actually form a flange")
    return errors


def validate_bulkhead(p: BulkheadParams) -> list[str]:
    errors = []
    if p.center_hole_diameter is not None and p.center_hole_diameter >= p.diameter * 0.5:
        errors.append(f"center_hole_diameter ({p.center_hole_diameter}mm) is too large for diameter ({p.diameter}mm)")
    if p.bolt_circle is not None:
        bc = p.bolt_circle
        if bc.bolt_circle_diameter + bc.bolt_hole_diameter >= p.diameter:
            errors.append("bolt_circle.bolt_circle_diameter + bolt_hole_diameter must be smaller than diameter")
        if p.center_hole_diameter is not None and bc.bolt_circle_diameter <= p.center_hole_diameter:
            errors.append("bolt_circle.bolt_circle_diameter must be larger than center_hole_diameter")
    if p.edge_chamfer >= p.thickness * 0.9:
        errors.append(f"edge_chamfer ({p.edge_chamfer}mm) is too large relative to thickness ({p.thickness}mm)")
    return errors


_VALIDATORS = {
    PartType.l_bracket: validate_l_bracket,
    PartType.flat_plate: validate_flat_plate,
    PartType.standoff: validate_standoff,
    PartType.flange: validate_flange,
    PartType.enclosure: validate_enclosure,
    PartType.shaft: validate_shaft,
    PartType.spring: validate_spring,
    PartType.gear: validate_gear,
    PartType.channel: validate_channel,
    PartType.bushing: validate_bushing,
    PartType.bulkhead: validate_bulkhead,
}


def validate(part_type: PartType, model) -> None:
    """Raises PartValidationError if any geometric constraint is violated."""
    errors = _VALIDATORS[part_type](model)
    if errors:
        raise PartValidationError(errors)
