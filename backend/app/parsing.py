"""Natural-language -> structured parameters, via a single forced
function-calling call to the Gemini API (free tier — see README). One
function per supported part category (mirroring the schemas in
app/schemas.py), plus an `unsupported_request` escape hatch the model calls
when the text doesn't describe one of the 5 categories.

Fields the model isn't confident about should be *omitted* (or null) rather
than guessed — app/resolve.py fills them in with documented defaults.
"""
from __future__ import annotations

import os

from google import genai
from google.genai import types

from app.schemas import PartType

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")

_NULL = {"type": "null"}


def _nullable(schema: dict) -> dict:
    return {"anyOf": [schema, _NULL]}


def _nullable_enum(values: list[str]) -> dict:
    return {"anyOf": [{"type": "string", "enum": values}, _NULL]}


_NUM = _nullable({"type": "number"})
_INT = _nullable({"type": "integer"})
_STR = _nullable({"type": "string"})

SYSTEM_PROMPT = """You convert a free-text description of a simple mechanical part into \
structured parameters for a parametric CAD generator. All dimensions are in millimeters.

Supported part categories, each with its own function:
- propose_l_bracket: an L-shaped / angle mounting bracket (two perpendicular legs)
- propose_flat_plate: a flat rectangular plate with a bolt-hole pattern
- propose_standoff: a round or hex standoff / spacer, optionally with a through-hole
- propose_flange: a circular flange with a center bore and a bolt circle
- propose_enclosure: a simple open-top rectangular enclosure/box with mounting holes
- propose_shaft: a shaft or pin, optionally stepped (multiple diameters) with chamfered ends

Rules:
1. Read the request and decide which ONE category it describes, then call that one function.
2. Only fill in a field if the text states it explicitly or it's an unambiguous, direct \
   restatement of the text (e.g. "60x40mm legs" -> leg1_length=60, leg2_length=40). \
   If a value isn't given, leave the field null — do NOT guess a plausible number. \
   Sensible engineering defaults are applied automatically downstream.
3. If the request does not describe any of the 5 supported categories (or is not a \
   mechanical part at all), call `unsupported_request` instead, with a brief reason.
4. Call exactly one function.
"""

_HOLE_PATTERN_SCHEMA = _nullable(
    {
        "type": "object",
        "description": "Hole layout on the plate. Omit entirely for the default corner pattern.",
        "properties": {
            "type": _nullable_enum(["corners", "grid", "linear"]),
            "edge_margin": _NUM,
            "rows": _INT,
            "cols": _INT,
            "spacing_x": _NUM,
            "spacing_y": _NUM,
            "hole_count": _INT,
            "spacing": _NUM,
            "orientation": _nullable_enum(["x", "y"]),
        },
    }
)

_CHAMFER_SCHEMA = _nullable(
    {"type": "object", "properties": {"size": _NUM, "angle_deg": _NUM}}
)


def _tool_schema(properties: dict) -> dict:
    return {
        "type": "object",
        "properties": {
            "name": _STR,
            "material": _STR,
            "parameters": {"type": "object", "properties": properties},
        },
        "required": ["parameters"],
    }


FUNCTION_DECLARATIONS = [
    types.FunctionDeclaration(
        name="propose_l_bracket",
        description="An L-shaped / right-angle mounting bracket with two perpendicular legs.",
        parameters_json_schema=_tool_schema(
            {
                "leg1_length": _NUM,
                "leg2_length": _NUM,
                "width": _NUM,
                "thickness": _NUM,
                "inner_fillet_radius": _NUM,
                "edge_fillet_radius": _NUM,
                "hole_diameter": _NUM,
                "holes_per_leg": _INT,
                "edge_margin": _NUM,
            }
        ),
    ),
    types.FunctionDeclaration(
        name="propose_flat_plate",
        description="A flat rectangular plate with a bolt-hole pattern.",
        parameters_json_schema=_tool_schema(
            {
                "length": _NUM,
                "width": _NUM,
                "thickness": _NUM,
                "corner_fillet_radius": _NUM,
                "hole_diameter": _NUM,
                "hole_pattern": _HOLE_PATTERN_SCHEMA,
            }
        ),
    ),
    types.FunctionDeclaration(
        name="propose_standoff",
        description="A round or hex standoff / spacer, optionally with a through-hole.",
        parameters_json_schema=_tool_schema(
            {
                "body_shape": _nullable_enum(["round", "hex"]),
                "outer_diameter": _NUM,
                "height": _NUM,
                "through_hole_diameter": _NUM,
            }
        ),
    ),
    types.FunctionDeclaration(
        name="propose_flange",
        description="A circular flange with a center bore and a bolt circle.",
        parameters_json_schema=_tool_schema(
            {
                "outer_diameter": _NUM,
                "thickness": _NUM,
                "bore_diameter": _NUM,
                "bolt_circle_diameter": _NUM,
                "bolt_count": _INT,
                "bolt_hole_diameter": _NUM,
                "fillet_radius": _NUM,
                "hub": _nullable(
                    {"type": "object", "properties": {"diameter": _NUM, "height": _NUM}}
                ),
            }
        ),
    ),
    types.FunctionDeclaration(
        name="propose_enclosure",
        description="A simple open-top rectangular enclosure/box with mounting holes.",
        parameters_json_schema=_tool_schema(
            {
                "length": _NUM,
                "width": _NUM,
                "height": _NUM,
                "wall_thickness": _NUM,
                "corner_fillet_radius": _NUM,
                "mounting_holes": _nullable(
                    {"type": "object", "properties": {"hole_diameter": _NUM, "inset": _NUM}}
                ),
            }
        ),
    ),
    types.FunctionDeclaration(
        name="propose_shaft",
        description="A shaft or pin, optionally stepped (multiple diameters) with chamfered ends.",
        parameters_json_schema=_tool_schema(
            {
                "segments": _nullable(
                    {
                        "type": "array",
                        "description": "Ordered list of {diameter, length} along the shaft axis.",
                        "items": {
                            "type": "object",
                            "properties": {"diameter": _NUM, "length": _NUM},
                        },
                    }
                ),
                "fillet_between_steps": _NUM,
                "start_chamfer": _CHAMFER_SCHEMA,
                "end_chamfer": _CHAMFER_SCHEMA,
            }
        ),
    ),
    types.FunctionDeclaration(
        name="unsupported_request",
        description="Call this when the request does not describe one of the 5 supported part categories.",
        parameters_json_schema={
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "Brief, user-facing explanation."},
            },
            "required": ["reason"],
        },
    ),
]

TOOL = types.Tool(function_declarations=FUNCTION_DECLARATIONS)

_TOOL_TO_PART_TYPE = {
    "propose_l_bracket": PartType.l_bracket,
    "propose_flat_plate": PartType.flat_plate,
    "propose_standoff": PartType.standoff,
    "propose_flange": PartType.flange,
    "propose_enclosure": PartType.enclosure,
    "propose_shaft": PartType.shaft,
}


class UnsupportedPartError(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


class ParsedPart:
    def __init__(self, part_type: PartType, name: str | None, material: str | None, raw_parameters: dict):
        self.part_type = part_type
        self.name = name
        self.material = material
        self.raw_parameters = raw_parameters


def parse_text(text: str) -> ParsedPart:
    """Call Gemini to classify + extract structured parameters from free text.
    Raises UnsupportedPartError if the request isn't one of the 5 categories.
    """
    client = genai.Client()

    response = client.models.generate_content(
        model=MODEL,
        contents=text,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[TOOL],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(mode="ANY")
            ),
        ),
    )

    calls = response.function_calls or []
    call = calls[0] if calls else None
    if call is None:
        raise UnsupportedPartError("Couldn't interpret that request as a mechanical part.")

    args = dict(call.args or {})

    if call.name == "unsupported_request":
        raise UnsupportedPartError(args.get("reason", "Unsupported part request."))

    part_type = _TOOL_TO_PART_TYPE.get(call.name)
    if part_type is None:
        raise UnsupportedPartError(f"Unrecognized function call: {call.name}")

    return ParsedPart(
        part_type=part_type,
        name=args.get("name"),
        material=args.get("material"),
        raw_parameters=args.get("parameters") or {},
    )
