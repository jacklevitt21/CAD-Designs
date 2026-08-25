"""Cross-field geometric validation beyond what Pydantic's field constraints
(gt=0, etc.) can express — e.g. "hole diameter must fit within the part".

Each function takes a fully-resolved, Pydantic-typed params model and returns
a list of human-readable error strings (empty list = valid).
"""
from __future__ import annotations

from app.resolve import PartValidationError
from app.schemas import (
    EnclosureParams,
    FlangeParams,
    FlatPlateParams,
    HolePatternCorners,
    HolePatternGrid,
    HolePatternLinear,
    LBracketParams,
    PartType,
    ShaftParams,
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


_VALIDATORS = {
    PartType.l_bracket: validate_l_bracket,
    PartType.flat_plate: validate_flat_plate,
    PartType.standoff: validate_standoff,
    PartType.flange: validate_flange,
    PartType.enclosure: validate_enclosure,
    PartType.shaft: validate_shaft,
}


def validate(part_type: PartType, model) -> None:
    """Raises PartValidationError if any geometric constraint is violated."""
    errors = _VALIDATORS[part_type](model)
    if errors:
        raise PartValidationError(errors)
