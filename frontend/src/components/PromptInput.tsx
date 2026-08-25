import { useState } from 'react'
import { EXAMPLE_PROMPTS } from '../examples'

interface Props {
  onSubmit: (text: string) => void
  disabled: boolean
}

export function PromptInput({ onSubmit, disabled }: Props) {
  const [text, setText] = useState('')

  function submit(value: string) {
    const trimmed = value.trim()
    if (trimmed) onSubmit(trimmed)
  }

  return (
    <div className="prompt-input">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          submit(text)
        }}
      >
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Describe a mounting bracket, standoff, flange, enclosure, or shaft…"
          rows={3}
          disabled={disabled}
        />
        <button type="submit" disabled={disabled || !text.trim()}>
          {disabled ? 'Generating…' : 'Generate CAD Model'}
        </button>
      </form>

      <div className="example-chips">
        {EXAMPLE_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            type="button"
            className="chip"
            disabled={disabled}
            onClick={() => {
              setText(prompt)
              submit(prompt)
            }}
          >
            {prompt.length > 42 ? prompt.slice(0, 42) + '…' : prompt}
          </button>
        ))}
      </div>
    </div>
  )
}
