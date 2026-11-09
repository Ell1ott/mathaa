export function Chip({ on, dim, count, children, onClick }) {
  return (
    <button type="button" className={'chip' + (on ? ' on' : '') + (dim ? ' z' : '')} onClick={onClick}>
      {children}
      {count != null && <small>{count}</small>}
    </button>
  )
}
