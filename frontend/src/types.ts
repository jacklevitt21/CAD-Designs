export type PartType =
  | 'l_bracket'
  | 'flat_plate'
  | 'standoff'
  | 'flange'
  | 'enclosure'
  | 'shaft'
  | 'spring'
  | 'gear'
  | 'channel'
  | 'bushing'
  | 'bulkhead'

export const PART_TYPE_LABELS: Record<PartType, string> = {
  l_bracket: 'L-Bracket',
  flat_plate: 'Flat Plate',
  standoff: 'Standoff / Spacer',
  flange: 'Flange',
  enclosure: 'Enclosure',
  shaft: 'Shaft / Pin',
  spring: 'Compression Spring',
  gear: 'Spur Gear',
  channel: 'C-Channel Bracket',
  bushing: 'Bushing / Sleeve',
  bulkhead: 'Bulkhead',
}

export interface PartResponse {
  part_id: string
  part_type: PartType
  name: string | null
  material: string | null
  parameters: Record<string, unknown>
  defaulted_fields: string[]
  warnings: string[]
  step_url: string
  stl_url: string
}

export interface ApiErrorDetail {
  errors?: string[]
}
