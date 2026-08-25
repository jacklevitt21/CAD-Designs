from __future__ import annotations

from pathlib import Path

import cadquery as cq

STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "storage"


def export_part(part_id: str, result: cq.Workplane) -> tuple[Path, Path]:
    """Export a generated part to STEP (CAD interop) and STL (web preview).
    Returns (step_path, stl_path).
    """
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    step_path = STORAGE_DIR / f"{part_id}.step"
    stl_path = STORAGE_DIR / f"{part_id}.stl"

    result.val().exportStep(str(step_path))
    cq.exporters.export(result, str(stl_path))

    return step_path, stl_path
