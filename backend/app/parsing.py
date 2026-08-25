"""Natural-language -> structured parameters, via a single forced tool-use
call to the Claude API. One tool per supported part category (mirroring the
schemas in app/schemas.py), plus an `unsupported_request` escape hatch the
model calls when the text doesn't describe one of the 5 categories.

Fields the model isn't confident about should be *omitted* (or null) rather
than guessed — app/resolve.py fills them in with documented defaults.
"""
from __future__ import annotations

import os

import anthropic

from app.schemas import PartType

MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-5")

_NUM = {"type": ["number", "null"]}
_INT = {"type": ["integer", "null"]}
_STR = {"type": ["string", "null"]}

SYSTEM_PROMPT = """You convert a free-text description of a simple mechanical part into \
structured parameters for a parametric CAD generator. All dimensions are in millimeters.

Supported part categories, each with its own tool:
- propose_l_bracket: an L-shaped / angle mounting bracket (two perpendicular legs)
- propose_flat_plate: a flat rectangular plate with a bolt-hole pattern
- propose_standoff: a round or hex standoff / spacer, optionally with a through-hole
- propose_flange: a circular flange with a center bore and a bolt circle
- propose_enclosure: a simple open-top rectangular enclosure/box with mounting holes
- propose_shaft: a shaft or pin, optionally stepped (multiple diameters) with chamfered ends

Rules:
1. Read the request and decide which ONE category it describes, then call that one tool.
2. Only fill in a field if the text states it explicitly or it's an unambiguous, direct \
   restatement of the text (e.g. "60x40mm legs" -> leg1_length=60, leg2_length=40). \
   If a value isn't given, leave the field null — do NOT guess a plausible number. \
   Sensible engineering defaults are applied automatically downstream.
3. If the request does not describe any of the 5 supported categories (or is not a \
   mechanical part at all), call `unsupported_request` instead, with a brief reason.
4. Call exactly one tool.
"""

_HOLE_PATTERN_SCHEMA = {
    "type": ["object", "null"],
    "description": "Hole layout on the plate. Omit entirely for the default corner pattern.",
    "properties": {
        "type": {"type": ["string", "null"], "enum": ["corners", "grid", "linear", None]},
        "edge_margin": _NUM,
        "rows": _INT,
        "cols": _INT,
        "spacing_x": _NUM,
        "spacing_y": _NUM,
        "hole_count": _INT,
        "spacing": _NUM,
        "orientation": {"type": ["string", "null"], "enum": ["x", "y", None]},
    },
}

_CHAMFER_SCHEMA = {
    "type": ["object", "null"],
    "properties": {"size": _NUM, "angle_deg": _NUM},
}

TOOLS = [
    {
        "name": "propose_l_bracket",
        "description": "An L-shaped / right-angle mounting bracket with two perpendicular legs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": _STR,
                "material": _STR,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "leg1_length": _NUM,
                        "leg2_length": _NUM,
                        "width": _NUM,
                        "thickness": _NUM,
                        "inner_fillet_radius": _NUM,
                        "edge_fillet_radius": _NUM,
                        "hole_diameter": _NUM,
                        "holes_per_leg": _INT,
                        "edge_margin": _NUM,
                    },
                },
            },
            "required": ["parameters"],
        },
    },
    {
        "name": "propose_flat_plate",
        "description": "A flat rectangular plate with a bolt-hole pattern.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": _STR,
                "material": _STR,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "length": _NUM,
                        "width": _NUM,
                        "thickness": _NUM,
                        "corner_fillet_radius": _NUM,
                        "hole_diameter": _NUM,
                        "hole_pattern": _HOLE_PATTERN_SCHEMA,
                    },
                },
            },
            "required": ["parameters"],
        },
    },
    {
        "name": "propose_standoff",
        "description": "A round or hex standoff / spacer, optionally with a through-hole.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": _STR,
                "material": _STR,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "body_shape": {"type": ["string", "null"], "enum": ["round", "hex", None]},
                        "outer_diameter": _NUM,
                        "height": _NUM,
                        "through_hole_diameter": _NUM,
                    },
                },
            },
            "required": ["parameters"],
        },
    },
    {
        "name": "propose_flange",
        "description": "A circular flange with a center bore and a bolt circle.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": _STR,
                "material": _STR,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "outer_diameter": _NUM,
                        "thickness": _NUM,
                        "bore_diameter": _NUM,
                        "bolt_circle_diameter": _NUM,
                        "bolt_count": _INT,
                        "bolt_hole_diameter": _NUM,
                        "fillet_radius": _NUM,
                        "hub": {
                            "type": ["object", "null"],
                            "properties": {"diameter": _NUM, "height": _NUM},
                        },
                    },
                },
            },
            "required": ["parameters"],
        },
    },
    {
        "name": "propose_enclosure",
        "description": "A simple open-top rectangular enclosure/box with mounting holes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": _STR,
                "material": _STR,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "length": _NUM,
                        "width": _NUM,
                        "height": _NUM,
                        "wall_thickness": _NUM,
                        "corner_fillet_radius": _NUM,
                        "mounting_holes": {
                            "type": ["object", "null"],
                            "properties": {"hole_diameter": _NUM, "inset": _NUM},
                        },
                    },
                },
            },
            "required": ["parameters"],
        },
    },
    {
        "name": "propose_shaft",
        "description": "A shaft or pin, optionally stepped (multiple diameters) with chamfered ends.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": _STR,
                "material": _STR,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "segments": {
                            "type": ["array", "null"],
                            "description": "Ordered list of {diameter, length} along the shaft axis.",
                            "items": {
                                "type": "object",
                                "properties": {"diameter": _NUM, "length": _NUM},
                            },
                        },
                        "fillet_between_steps": _NUM,
                        "start_chamfer": _CHAMFER_SCHEMA,
                        "end_chamfer": _CHAMFER_SCHEMA,
                    },
                },
            },
            "required": ["parameters"],
        },
    },
    {
        "name": "unsupported_request",
        "description": "Call this when the request does not describe one of the 5 supported part categories.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "Brief, user-facing explanation."},
            },
            "required": ["reason"],
        },
    },
]

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
    """Call Claude to classify + extract structured parameters from free text.
    Raises UnsupportedPartError if the request isn't one of the 5 categories.
    """
    client = anthropic.Anthropic()

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=TOOLS,
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": text}],
    )

    tool_use = next((b for b in response.content if b.type == "tool_use"), None)
    if tool_use is None:
        raise UnsupportedPartError("Couldn't interpret that request as a mechanical part.")

    if tool_use.name == "unsupported_request":
        raise UnsupportedPartError(tool_use.input.get("reason", "Unsupported part request."))

    part_type = _TOOL_TO_PART_TYPE.get(tool_use.name)
    if part_type is None:
        raise UnsupportedPartError(f"Unrecognized tool call: {tool_use.name}")

    return ParsedPart(
        part_type=part_type,
        name=tool_use.input.get("name"),
        material=tool_use.input.get("material"),
        raw_parameters=tool_use.input.get("parameters") or {},
    )
