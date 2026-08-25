import { useEffect, useState } from 'react'
import type { PartResponse } from '../types'
import { PART_TYPE_LABELS } from '../types'

interface Props {
  part: PartResponse
  onRegenerate: (name: string | null, material: string | null, parameters: Record<string, unknown>) => void
  isRegenerating: boolean
}

/** Editable string form of every parameter value. Scalars edit directly;
 * objects/arrays (hole_pattern, hub, segments, ...) edit as raw JSON. */
type FieldDraft = Record<string, string>

function toDraft(parameters: Record<string, unknown>): FieldDraft {
  const draft: FieldDraft = {}
  for (const [key, value] of Object.entries(parameters)) {
    if (value === null) draft[key] = ''
    else if (typeof value === 'object') draft[key] = JSON.stringify(value, null, 2)
    else draft[key] = String(value)
  }
  return draft
}

function parseDraftValue(original: unknown, raw: string): unknown {
  if (original !== null && typeof original === 'object') {
    return JSON.parse(raw) // caller catches
  }
  if (raw.trim() === '') return null
  if (typeof original === 'number' || original === null) {
    const n = Number(raw)
    if (!Number.isNaN(n) && raw.trim() !== '') return n
  }
  return raw
}

export function ParamsPanel({ part, onRegenerate, isRegenerating }: Props) {
  const [name, setName] = useState(part.name ?? '')
  const [material, setMaterial] = useState(part.material ?? '')
  const [draft, setDraft] = useState<FieldDraft>(() => toDraft(part.parameters))
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    setName(part.name ?? '')
    setMaterial(part.material ?? '')
    setDraft(toDraft(part.parameters))
    setFieldErrors({})
  }, [part.part_id])

  function handleRegenerate() {
    const parameters: Record<string, unknown> = {}
    const errors: Record<string, string> = {}

    for (const [key, raw] of Object.entries(draft)) {
      try {
        parameters[key] = parseDraftValue(part.parameters[key], raw)
      } catch {
        errors[key] = 'Invalid JSON'
      }
    }

    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return

    onRegenerate(name.trim() || null, material.trim() || null, parameters)
  }

  const isNested = (key: string) => {
    const v = part.parameters[key]
    return v !== null && typeof v === 'object'
  }

  return (
    <div className="params-panel">
      <div className="params-header">
        <span className="part-type-badge">{PART_TYPE_LABELS[part.part_type]}</span>
      </div>

      <label className="field">
        <span>Name</span>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="(unnamed)" />
      </label>

      <label className="field">
        <span>Material</span>
        <input value={material} onChange={(e) => setMaterial(e.target.value)} placeholder="(not specified)" />
      </label>

      <div className="params-list">
        {Object.entries(draft).map(([key, value]) => (
          <label className="field" key={key}>
            <span>
              {key}
              {part.defaulted_fields.includes(key) && <span className="default-badge">default</span>}
            </span>
            {isNested(key) ? (
              <textarea
                value={value}
                rows={Math.min(8, value.split('\n').length + 1)}
                onChange={(e) => setDraft((d) => ({ ...d, [key]: e.target.value }))}
              />
            ) : (
              <input value={value} onChange={(e) => setDraft((d) => ({ ...d, [key]: e.target.value }))} />
            )}
            {fieldErrors[key] && <span className="field-error">{fieldErrors[key]}</span>}
          </label>
        ))}
      </div>

      <button type="button" className="regenerate-btn" onClick={handleRegenerate} disabled={isRegenerating}>
        {isRegenerating ? 'Regenerating…' : 'Apply Changes & Regenerate'}
      </button>

      {part.warnings.length > 0 && (
        <ul className="warnings">
          {part.warnings.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
