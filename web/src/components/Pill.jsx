import { useEffect, useLayoutEffect, useRef, useState } from 'react'

function Pill({ label, onRemove }) {
  return (
    <span className="pill">
      {label}
      <i role="button" tabIndex={0} aria-label="Remove" onClick={onRemove}>✕</i>
    </span>
  )
}

export function PillRow({ pills, onRemove, menuRef }) {
  const wrapRef = useRef(null)
  const rowRef = useRef(null)
  const moreRef = useRef(null)
  const [cut, setCut] = useState(0)
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    menuRef.current = {
      isOpen: () => menuOpen,
      close: () => setMenuOpen(false),
    }
  }, [menuOpen, menuRef])

  useLayoutEffect(() => {
    const row = rowRef.current
    const more = moreRef.current
    if (!row || !more) return
    const items = [...row.querySelectorAll('.pill:not(.more)')]
    items.forEach((el) => { el.hidden = false })
    more.hidden = true
    setMenuOpen(false)
    if (row.clientWidth < 8) {
      setCut(0)
      return
    }
    let n = 0
    while (row.scrollWidth > row.clientWidth + 1) {
      const visible = items.filter((el) => !el.hidden)
      if (!visible.length) break
      visible[visible.length - 1].hidden = true
      n += 1
      more.hidden = false
      more.textContent = '+' + n
    }
    setCut(n)
  }, [pills])

  useEffect(() => {
    if (!menuOpen) return
    function onDoc(e) {
      if (!wrapRef.current?.contains(e.target)) setMenuOpen(false)
    }
    document.addEventListener('click', onDoc)
    return () => document.removeEventListener('click', onDoc)
  }, [menuOpen])

  const hidden = pills.slice(pills.length - cut)

  return (
    <span className="pillwrap" ref={wrapRef}>
      <span className="pills" id="pills" ref={rowRef}>
        {pills.map((pill, index) => (
          <span key={pill.id} hidden={index >= pills.length - cut && cut > 0} className="pill">
            {pill.label}
            <i role="button" tabIndex={0} aria-label="Remove" onClick={() => onRemove(pill)}>✕</i>
          </span>
        ))}
        <button
          type="button"
          ref={moreRef}
          className="pill more"
          hidden={cut === 0}
          aria-expanded={menuOpen}
          aria-label={cut ? cut + ' more filters' : undefined}
          onClick={() => setMenuOpen((open) => !open)}
        >
          {cut ? '+' + cut : ''}
        </button>
      </span>
      <div className="pmenu" hidden={!menuOpen || cut === 0}>
        {hidden.map((pill) => <Pill key={pill.id} label={pill.label} onRemove={() => onRemove(pill)} />)}
      </div>
    </span>
  )
}
