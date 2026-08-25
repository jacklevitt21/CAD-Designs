"""Geometric constraint violations must be caught before CadQuery ever runs."""
import pytest

from app.resolve import PartValidationError, resolve_parameters
from app.schemas import PartType
from app.validation import validate


def test_hole_too_large_for_bracket_thickness():
    resolved = resolve_parameters(PartType.l_bracket, {"thickness": 2, "hole_diameter": 50})
    with pytest.raises(PartValidationError):
        validate(PartType.l_bracket, resolved.model)


def test_bore_larger_than_bolt_circle_rejected():
    resolved = resolve_parameters(
        PartType.flange, {"bore_diameter": 70, "bolt_circle_diameter": 60, "outer_diameter": 80}
    )
    with pytest.raises(PartValidationError):
        validate(PartType.flange, resolved.model)


def test_wall_thickness_too_large_for_enclosure():
    resolved = resolve_parameters(PartType.enclosure, {"length": 20, "width": 20, "wall_thickness": 15})
    with pytest.raises(PartValidationError):
        validate(PartType.enclosure, resolved.model)


def test_pydantic_rejects_negative_dimension():
    with pytest.raises(PartValidationError):
        resolve_parameters(PartType.standoff, {"outer_diameter": -5})
