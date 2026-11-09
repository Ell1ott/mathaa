export function Empty({ title, children, onClear }) {
  return (
    <div className="empty">
      <b>{title}</b>
      {children}
      <br />
      <button type="button" onClick={onClear}>Clear filters</button>
    </div>
  )
}
