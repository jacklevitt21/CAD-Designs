interface Props {
  message: string
  errors?: string[] | null
  onDismiss?: () => void
}

export function ErrorBanner({ message, errors, onDismiss }: Props) {
  return (
    <div className="error-banner">
      <div className="error-banner-header">
        <strong>{message}</strong>
        {onDismiss && (
          <button type="button" className="dismiss" onClick={onDismiss} aria-label="Dismiss">
            ×
          </button>
        )}
      </div>
      {errors && errors.length > 0 && (
        <ul>
          {errors.map((err) => (
            <li key={err}>{err}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
