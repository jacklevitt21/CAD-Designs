from __future__ import annotations

import re
import uuid

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.generation.export import STORAGE_DIR, export_part
from app.generation.registry import generate_part
from app.parsing import UnsupportedPartError, parse_text
from app.resolve import PartValidationError, resolve_parameters
from app.schemas import GenerateTextRequest, PartResponse, PartType, RegenerateRequest
from app.validation import validate

load_dotenv()

app = FastAPI(title="Text-to-CAD API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STORAGE_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/files", StaticFiles(directory=str(STORAGE_DIR)), name="files")


SUPPORTED_CATEGORIES_MESSAGE = (
    "Supported part categories: mounting brackets (L-brackets, flat plates with bolt "
    "patterns), standoffs/spacers, circular flanges with bolt circles, simple open-top "
    "enclosures with mounting holes, and shafts/pins (optionally stepped, with chamfers). "
    "Try rephrasing your request to describe one of these."
)


def _build_part_response(part_type: PartType, name, material, resolved) -> PartResponse:
    warnings: list[str] = []
    try:
        result = generate_part(part_type, resolved.model)
    except Exception as exc:  # CadQuery construction failure (e.g. degenerate geometry)
        raise HTTPException(
            status_code=422,
            detail=f"Could not generate geometry from these parameters: {exc}",
        ) from exc

    part_id = uuid.uuid4().hex
    export_part(part_id, result)

    return PartResponse(
        part_id=part_id,
        part_type=part_type,
        name=name,
        material=material,
        parameters=resolved.parameters,
        defaulted_fields=resolved.defaulted_fields,
        warnings=warnings,
        step_url=f"/files/{part_id}.step",
        stl_url=f"/files/{part_id}.stl",
    )


@app.post("/api/generate", response_model=PartResponse)
def generate_from_text(req: GenerateTextRequest) -> PartResponse:
    try:
        parsed = parse_text(req.text)
    except UnsupportedPartError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"{exc.reason} {SUPPORTED_CATEGORIES_MESSAGE}",
        ) from exc
    except anthropic.AuthenticationError as exc:
        raise HTTPException(
            status_code=500,
            detail="Server is missing a valid ANTHROPIC_API_KEY. See backend/README for setup.",
        ) from exc
    except anthropic.APIError as exc:
        raise HTTPException(status_code=502, detail=f"Claude API error: {exc}") from exc

    try:
        resolved = resolve_parameters(parsed.part_type, parsed.raw_parameters)
        validate(parsed.part_type, resolved.model)
    except PartValidationError as exc:
        raise HTTPException(status_code=422, detail={"errors": exc.errors}) from exc

    return _build_part_response(parsed.part_type, parsed.name, parsed.material, resolved)


@app.post("/api/regenerate", response_model=PartResponse)
def regenerate(req: RegenerateRequest) -> PartResponse:
    try:
        resolved = resolve_parameters(req.part_type, req.parameters)
        validate(req.part_type, resolved.model)
    except PartValidationError as exc:
        raise HTTPException(status_code=422, detail={"errors": exc.errors}) from exc

    return _build_part_response(req.part_type, req.name, req.material, resolved)


_PART_ID_RE = re.compile(r"^[0-9a-f]{32}$")


@app.get("/api/download/step/{part_id}")
def download_step(part_id: str) -> FileResponse:
    if not _PART_ID_RE.fullmatch(part_id):
        raise HTTPException(status_code=404, detail="Part not found")
    path = STORAGE_DIR / f"{part_id}.step"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Part not found")
    return FileResponse(path, filename=f"{part_id}.step", media_type="application/step")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
