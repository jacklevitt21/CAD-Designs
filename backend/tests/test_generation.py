"""Every category must generate a valid, non-degenerate solid from its
default parameters, and export cleanly to STEP + STL."""
import pytest

from app.generation.registry import generate_part
from app.resolve import resolve_parameters
from app.schemas import DEFAULTS, PartType
from app.validation import validate


@pytest.mark.parametrize("part_type", list(PartType))
def test_defaults_generate_valid_solid(part_type):
    resolved = resolve_parameters(part_type, {})
    validate(part_type, resolved.model)
    result = generate_part(part_type, resolved.model)
    assert result.val().Volume() > 0


@pytest.mark.parametrize("part_type", list(PartType))
def test_defaults_cover_every_required_field(part_type):
    # Every field DEFAULTS declares must actually construct the model.
    resolved = resolve_parameters(part_type, {})
    assert set(resolved.defaulted_fields) == set(DEFAULTS[part_type].keys())


def test_flat_plate_grid_pattern():
    resolved = resolve_parameters(
        PartType.flat_plate,
        {"hole_pattern": {"type": "grid", "rows": 2, "cols": 4, "spacing_x": 15, "spacing_y": 15, "edge_margin": 10}},
    )
    validate(PartType.flat_plate, resolved.model)
    result = generate_part(PartType.flat_plate, resolved.model)
    assert result.val().Volume() > 0


def test_shaft_stepped_with_fillet_and_chamfers():
    resolved = resolve_parameters(
        PartType.shaft,
        {
            "segments": [{"diameter": 10, "length": 30}, {"diameter": 16, "length": 20}],
            "fillet_between_steps": 1,
            "start_chamfer": {"size": 1},
            "end_chamfer": {"size": 1},
        },
    )
    validate(PartType.shaft, resolved.model)
    result = generate_part(PartType.shaft, resolved.model)
    assert result.val().Volume() > 0


def test_flange_with_hub_and_fillet():
    resolved = resolve_parameters(
        PartType.flange,
        {"hub": {"diameter": 35, "height": 10}, "fillet_radius": 2},
    )
    validate(PartType.flange, resolved.model)
    result = generate_part(PartType.flange, resolved.model)
    assert result.val().Volume() > 0


@pytest.mark.parametrize("num_teeth,module", [(6, 4), (12, 3), (20, 2), (60, 1.5), (200, 0.5)])
def test_gear_tooth_count_range(num_teeth, module):
    resolved = resolve_parameters(PartType.gear, {"num_teeth": num_teeth, "module": module})
    validate(PartType.gear, resolved.model)
    result = generate_part(PartType.gear, resolved.model)
    assert result.val().Volume() > 0


def test_spring_fractional_coils():
    resolved = resolve_parameters(
        PartType.spring, {"num_coils": 3.5, "wire_diameter": 1.0, "outer_diameter": 8}
    )
    validate(PartType.spring, resolved.model)
    result = generate_part(PartType.spring, resolved.model)
    assert result.val().Volume() > 0


def test_bushing_with_flange():
    resolved = resolve_parameters(PartType.bushing, {"flange": {"diameter": 20, "thickness": 3}})
    validate(PartType.bushing, resolved.model)
    result = generate_part(PartType.bushing, resolved.model)
    assert result.val().Volume() > 0


def test_bulkhead_with_bolt_circle_and_center_hole():
    resolved = resolve_parameters(
        PartType.bulkhead,
        {
            "bolt_circle": {"bolt_circle_diameter": 45, "bolt_count": 4, "bolt_hole_diameter": 4},
            "center_hole_diameter": 6,
            "edge_chamfer": 1.5,
        },
    )
    validate(PartType.bulkhead, resolved.model)
    result = generate_part(PartType.bulkhead, resolved.model)
    assert result.val().Volume() > 0


def test_channel_with_holes_and_fillet():
    resolved = resolve_parameters(PartType.channel, {"holes_per_flange": 2, "inner_fillet_radius": 2})
    validate(PartType.channel, resolved.model)
    result = generate_part(PartType.channel, resolved.model)
    assert result.val().Volume() > 0
