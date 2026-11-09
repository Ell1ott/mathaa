export function Segment({ options, className, label }) {
  return (
    <div className={className || 'seg'} role="tablist" aria-label={label}>
      {options.map((opt) => (
        <button
          key={opt.key ?? opt.value}
          type="button"
          role="tab"
          className={(opt.on ? 'on ' : '') + (opt.dim ? 'z' : '')}
          disabled={opt.disabled}
          aria-label={opt.aria}
          aria-selected={opt.on || undefined}
          onClick={opt.onClick}
        >
          {opt.icon}
          {opt.icon ? <span>{opt.label}</span> : opt.label}
        </button>
      ))}
    </div>
  )
}
