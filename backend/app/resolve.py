"""Merge partial (LLM-extracted or user-edited) parameters with per-category
defaults, and validate the result into a fully-typed parameter model.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, ValidationError

from app.schemas import DEFAULTS, PARAM_MODELS, PartType

# Defaults for nested sub-objects the LLM may only partially fill in (e.g. it
# catches "grid of holes, 3 rows" but not spacing). Keyed by the parent field
# name; for the discriminated `hole_pattern` union, keyed again by `type`.
NESTED_DEFAULTS: dict[str, dict] = {
    "hole_pattern": {
        "corners": {"type": "corners", "edge_margin": 8.0},
        "grid": {"type": "grid", "rows": 2, "cols": 2, "spacing_x": 20.0, "spacing_y": 20.0, "edge_margin": 8.0},
        "linear": {"type": "linear", "hole_count": 2, "spacing": 20.0, "edge_margin": 8.0, "orientation": "x"},
    },
    "mounting_holes": {"hole_diameter": 4.0, "inset": 8.0},
    "hub": {"diameter": 30.0, "height": 10.0},
    "start_chamfer": {"size": 1.0, "angle_deg": 45.0},
    "end_chamfer": {"size": 1.0, "angle_deg": 45.0},
}
SEGMENT_DEFAULT = {"diameter": 10.0, "length": 20.0}


def _fill_nested_defaults(key: str, value: object) -> object:
    """Fill in missing sub-fields of a partially-specified nested object
    (e.g. LLM gave hole_pattern.type + rows but not spacing_x)."""
    if key == "segments" and isinstance(value, list):
        return [{**SEGMENT_DEFAULT, **seg} for seg in value if isinstance(seg, dict)]

    if not isinstance(value, dict):
        return value

    if key == "hole_pattern":
        variant = value.get("type") or "corners"
        base = NESTED_DEFAULTS["hole_pattern"].get(variant, NESTED_DEFAULTS["hole_pattern"]["corners"])
        return {**base, **value}

    if key in NESTED_DEFAULTS:
        return {**NESTED_DEFAULTS[key], **value}

    return value


class ResolvedParams(BaseModel):
    part_type: PartType
    parameters: dict
    defaulted_fields: list[str]
    model: BaseModel

    model_config = ConfigDict(arbitrary_types_allowed=True)


class PartValidationError(Exception):
    """Raised when parameters fail validation. Carries user-facing messages."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def resolve_parameters(part_type: PartType, raw_parameters: dict) -> ResolvedParams:
    """Fill omitted/None top-level keys with category defaults, tracking which
    keys were defaulted, then validate the merged dict against the category's
    Pydantic model.
    """
    defaults = DEFAULTS[part_type]
    raw_parameters = raw_parameters or {}

    merged: dict = {}
    defaulted_fields: list[str] = []
    for key, default_value in defaults.items():
        if key in raw_parameters and raw_parameters[key] is not None:
            merged[key] = _fill_nested_defaults(key, raw_parameters[key])
        else:
            merged[key] = default_value
            defaulted_fields.append(key)

    # Pass through any required fields that have no default (e.g. bore_diameter
    # has a default above, but a field with no entry in DEFAULTS must come
    # from raw_parameters or Pydantic will raise a clear "field required" error).
    for key, value in raw_parameters.items():
        if key not in merged and value is not None:
            merged[key] = value

    model_cls = PARAM_MODELS[part_type]
    try:
        model = model_cls.model_validate(merged)
    except ValidationError as exc:
        messages = [
            f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors()
        ]
        raise PartValidationError(messages) from exc

    return ResolvedParams(
        part_type=part_type,
        parameters=model.model_dump(),
        defaulted_fields=defaulted_fields,
        model=model,
    )
