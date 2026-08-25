import type { PartResponse, PartType } from './types'

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
  const res = await fetch('/api/generate', {
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
  const res = await fetch('/api/regenerate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ part_type: partType, name, material, parameters }),
  })
  return handleResponse(res)
}

export function stepDownloadUrl(partId: string): string {
  return `/api/download/step/${partId}`
}
