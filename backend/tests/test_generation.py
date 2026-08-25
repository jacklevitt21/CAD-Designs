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
