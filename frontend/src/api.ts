import type { PartResponse, PartType } from './types'

// In local dev this is empty and Vite's dev-server proxy forwards /api and
// /files to the backend (see vite.config.ts). In production the frontend and
// backend are typically deployed separately, so VITE_API_BASE_URL points at
// the deployed backend's origin (set at build time), e.g.
// https://text-to-cad-backend.onrender.com
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`
}

export class ApiError extends Error {
  status: number
  errors?: string[]

  constructor(message: string, status: number, errors?: string[]) {
    super(message)
    this.status = status
    this.errors = errors
  }
}

async function handleResponse(res: Response): Promise<PartResponse> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const detail = body.detail
    if (detail && typeof detail === 'object' && Array.isArray(detail.errors)) {
      throw new ApiError('Validation failed', res.status, detail.errors)
    }
    const message = typeof detail === 'string' ? detail : 'Request failed'
    throw new ApiError(message, res.status)
  }
  return res.json()
}

export async function generateFromText(text: string): Promise<PartResponse> {
  const res = await fetch(apiUrl('/api/generate'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  })
  return handleResponse(res)
}

export async function regenerate(
  partType: PartType,
  name: string | null,
  material: string | null,
  parameters: Record<string, unknown>,
): Promise<PartResponse> {
  const res = await fetch(apiUrl('/api/regenerate'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ part_type: partType, name, material, parameters }),
  })
  return handleResponse(res)
}

export function stepDownloadUrl(partId: string): string {
  return apiUrl(`/api/download/step/${partId}`)
}
