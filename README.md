# Text-to-CAD

Type a plain-English description of a mechanical part — get back a real, parametric
3D model you can orbit/zoom in the browser and download as a STEP file that opens
natively in SolidWorks, Fusion 360, Creo, etc.

```
"Aluminum L-bracket for avionics mount, 60x40mm legs, 5mm thick, 4 mounting holes 6mm near the corners"
```
→ parsed into structured parameters → generated as real B-rep solid geometry → previewed in 3D → downloadable STEP.

## Supported part categories

| Category | Examples |
|---|---|
| Mounting brackets | L-brackets, flat plates with bolt-hole patterns |
| Standoffs / spacers | round or hex, with optional through-hole |
| Flanges | circular, with a bore and a bolt circle |
| Enclosures | simple open-top boxes with corner mounting holes |
| Shafts / pins | optionally stepped (multiple diameters), with chamfers |

Requests outside these five categories are rejected with a clear explanation rather
than guessed at.

## Architecture

```
┌─────────────┐   text    ┌──────────────┐  function-calling  ┌───────────────┐
│   Frontend   │──────────▶│   FastAPI    │───────────────────▶│  Gemini API   │
│ React + r3f  │           │   backend    │◀───────────────────│ (extraction)  │
└─────────────┘           └──────┬───────┘   structured JSON  └───────────────┘
       ▲                          │
       │ STL (preview)            ▼
       │ STEP (download)   ┌──────────────┐
       └───────────────────│  CadQuery    │
                            │  generators  │
                            └──────────────┘
```

1. **Parsing** (`backend/app/parsing.py`) — the user's free text is sent to the
   Gemini API with one *function declaration* per part category (plus an
   `unsupported_request` escape hatch). `FunctionCallingConfig(mode="ANY")`
   forces Gemini to classify the request and extract only the values it's
   confident about — fields it can't find in the text are left `null` rather
   than guessed. (Gemini's `gemini-3.5-flash` was picked specifically because
   it has a genuine free tier — see **Cost** below.)
2. **Resolution** (`backend/app/resolve.py`) — the extracted (partial) parameters
   are merged with per-category defaults (`backend/app/schemas.py::DEFAULTS`),
   tracking which fields were filled in vs. user-specified, then validated into
   a typed Pydantic model.
3. **Validation** (`backend/app/validation.py`) — cross-field geometric checks
   (e.g. "hole diameter must fit within the part") run before any CAD kernel
   call, surfacing clear errors instead of letting CadQuery fail with an opaque
   OCCT exception.
4. **Generation** (`backend/app/generation/`) — one function per category builds
   the part as a CadQuery `Workplane`/solid, then exports both a STEP file
   (`.step`, for CAD interop) and an STL mesh (`.stl`, for the web viewer).
5. **Frontend** (`frontend/`) — React + `@react-three/fiber`. The prompt box
   posts to `/api/generate`; the returned STL streams into a `<Canvas>` with
   orbit/zoom/pan controls. A side panel shows every resolved parameter,
   flags which ones were defaulted, and lets you edit and hit "Regenerate"
   (which calls `/api/regenerate` — no LLM round-trip needed for a param tweak).

### Why this design

- **Structured extraction, not free-form generation.** The LLM never touches
  geometry — it only fills in a fixed, typed parameter schema per category.
  CadQuery is the single source of truth for what gets built, so output is
  always a valid, well-formed solid.
- **Defaults are explicit and shown to the user.** Every category has a
  documented default for every field; the UI distinguishes "you said this" from
  "we assumed this," and edits + regenerate never re-invoke the LLM.
- **Validation runs before the CAD kernel.** Geometric sanity checks give a
  human-readable error ("hole_diameter is too large for the plate") instead of
  a wall of OpenCascade stack trace.

## Project layout

```
backend/
  app/
    schemas.py       Pydantic parameter models + per-category defaults
    resolve.py        merge partial params with defaults, track what was defaulted
    validation.py      cross-field geometric validation
    parsing.py          Gemini API function-calling call (NL -> structured params)
    generation/
      l_bracket.py, flat_plate.py, standoff.py, flange.py, enclosure.py, shaft.py
      common.py         shared CadQuery helpers (hole drilling, etc.)
      export.py          STEP + STL export
      registry.py         part_type -> generator dispatch
    main.py               FastAPI app (/api/generate, /api/regenerate, /api/download/step/{id})
  tests/                pytest suite (generation, validation, API)
frontend/
  src/
    components/          PromptInput, Viewer3D, ParamsPanel, ErrorBanner
    api.ts                 typed fetch client
    types.ts                 shared TS types mirroring the backend schemas
    examples.ts               preset example prompts (chips)
```

## Running locally

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # then edit .env and set GEMINI_API_KEY
uvicorn app.main:app --reload --port 8000
```

Get a **free** API key at https://aistudio.google.com/apikey (no credit card
required; not available in the EU/UK/Switzerland). Without it, `/api/generate`
returns a clear 500 explaining the key is missing — `/api/regenerate` (used by
the "Apply Changes" button) doesn't call the LLM at all, so it works regardless.

### Cost

`gemini-3.5-flash`'s free tier covers interactive use and demoing at no cost.
The actual observed per-project limit (from a live 429 response, which is
more reliable than third-party blog posts — published numbers vary) was
**5 requests/minute** for this model; back-to-back rapid testing can hit that,
but normal interactive use (a person typing, reading the result, trying
another prompt) won't. If you outgrow it, or you're in a region without
free-tier access, swap in a paid Gemini tier or another provider by editing
`backend/app/parsing.py` — everything downstream (`resolve.py`,
`validation.py`, the CadQuery generators, the whole frontend) is decoupled
from the parsing layer via the `ParsedPart` interface, so nothing else needs
to change.

Run tests:

```bash
pytest
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — the Vite dev server proxies `/api` and `/files`
to the backend on port 8000 (see `frontend/vite.config.ts`).

## API

| Endpoint | Description |
|---|---|
| `POST /api/generate` | `{text}` → parses via Gemini, validates, generates. Returns a `PartResponse`. |
| `POST /api/regenerate` | `{part_type, name, material, parameters}` → re-validates & regenerates without calling the LLM. |
| `GET /api/download/step/{part_id}` | Downloads the generated STEP file. |
| `GET /files/{part_id}.stl` | Static STL mesh for the 3D preview. |

`PartResponse`:
```json
{
  "part_id": "…",
  "part_type": "l_bracket",
  "name": "Avionics L-Bracket",
  "material": "Aluminum 6061",
  "parameters": { "leg1_length": 60, "leg2_length": 40, "thickness": 5, "...": "..." },
  "defaulted_fields": ["thickness", "inner_fillet_radius", "..."],
  "warnings": [],
  "step_url": "/files/<id>.step",
  "stl_url": "/files/<id>.stl"
}
```
