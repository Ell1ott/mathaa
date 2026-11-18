import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

const CATEGORY_COLORS = {
  Mathematics: '#0a84ff',
  Sciences: '#34c759',
  'Individuals and societies': '#ff9500',
  'Language acquisition': '#af52de',
  'Studies in language and literature': '#ff2d55',
  Arts: '#5856d6',
}

function CategoryIcon({ name }) {
  const common = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.6, strokeLinecap: 'round', strokeLinejoin: 'round' }
  if (name === 'Mathematics') {
    return <svg viewBox="0 0 20 20" aria-hidden="true"><path {...common} d="M14.2 4.6H7.4l4 5.4-4 5.4h6.8" /></svg>
  }
  if (name === 'Sciences') {
    return (
      <svg viewBox="0 0 20 20" aria-hidden="true">
        <circle {...common} cx="10" cy="10" r="1.9" />
        <ellipse {...common} cx="10" cy="10" rx="7" ry="3.1" transform="rotate(45 10 10)" />
        <ellipse {...common} cx="10" cy="10" rx="7" ry="3.1" transform="rotate(-45 10 10)" />
      </svg>
    )
  }
  if (name === 'Individuals and societies') {
    return (
      <svg viewBox="0 0 20 20" aria-hidden="true">
        <circle {...common} cx="10" cy="10" r="6.4" />
        <path {...common} d="M3.6 10h12.8M10 3.6c1.8 2 2.7 4.1 2.7 6.4S11.8 14.4 10 16.4C8.2 14.4 7.3 12.3 7.3 10S8.2 5.6 10 3.6Z" />
      </svg>
    )
  }
  if (name === 'Language acquisition') {
    return (
      <svg viewBox="0 0 20 20" aria-hidden="true">
        <path {...common} d="M16.2 10.6c0 3.1-2.8 5.6-6.2 5.6-.8 0-1.6-.1-2.3-.4l-3.4 1 1-2.8c-1.1-1-1.7-2.4-1.7-3.9 0-3.1 2.8-5.6 6.2-5.6s6.4 2.5 6.4 6.1Z" />
        <path {...common} d="M7.8 12.1 10 7.1l2.2 5M8.6 10.6h2.8" />
      </svg>
    )
  }
  if (name === 'Studies in language and literature') {
    return (
      <svg viewBox="0 0 20 20" aria-hidden="true">
        <path {...common} d="M10 5.3C8.9 4.4 7.4 4 5.6 4H3.4v10.4h2.7c1.6 0 2.9.4 3.9 1.3 1-.9 2.3-1.3 3.9-1.3h2.7V4h-2.2c-1.8 0-3.3.4-4.4 1.3Z" />
        <path {...common} d="M10 5.3v10.4" />
      </svg>
    )
  }
  if (name === 'Arts') {
    return (
      <svg viewBox="0 0 20 20" aria-hidden="true">
        <path {...common} d="M10 3.5a6.5 6.5 0 1 0 0 13c1.2 0 1.6-.8 1.6-1.6 0-.9.7-1.6 1.7-1.6h1.3a2.2 2.2 0 0 0 2.2-2.2A6.6 6.6 0 0 0 10 3.5Z" />
        <circle cx="7.2" cy="7.4" r="1" fill="currentColor" />
        <circle cx="11" cy="6.3" r="1" fill="currentColor" />
        <circle cx="6.2" cy="11.2" r="1" fill="currentColor" />
      </svg>
    )
  }
  return <svg viewBox="0 0 20 20" aria-hidden="true"><path {...common} d="M3.5 6.2A1.7 1.7 0 0 1 5.2 4.5h2.6l1.3 1.4h5.7a1.7 1.7 0 0 1 1.7 1.7v6.7a1.7 1.7 0 0 1-1.7 1.7H5.2a1.7 1.7 0 0 1-1.7-1.7Z" /></svg>
}

function Check() {
  return (
    <svg className="scheck" viewBox="0 0 16 16" aria-hidden="true">
      <path d="M3.3 8.4 6.4 11.5 12.7 4.9" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function Pin({ filled, className }) {
  return (
    <svg className={className} viewBox="0 0 16 16" aria-hidden="true">
      <path d="M9.7 1.9a.75.75 0 0 1 1 0l3.4 3.4a.75.75 0 0 1-.35 1.26l-1.7.32-2.15 2.15-.1 2.55a.75.75 0 0 1-1.27.55L6.1 9.9l-2.55 2.55a.65.65 0 0 1-.92-.92L5.2 8.98l-2.2-2.43a.75.75 0 0 1 .55-1.26l2.55-.1L8.25 3.04l.32-1.7a.75.75 0 0 1 .57-.5Z" fill={filled ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="1.15" strokeLinejoin="round" />
    </svg>
  )
}

function Search() {
  return (
    <svg className="ssearch" viewBox="0 0 20 20" aria-hidden="true">
      <circle cx="8.6" cy="8.6" r="5.4" fill="none" stroke="currentColor" strokeWidth="1.7" />
      <path d="m12.7 12.7 4 4" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  )
}

function colorFor(name) {
  return CATEGORY_COLORS[name] || '#8e8e93'
}

const PIN_KEY = 'ibq-subject-pins'

function loadPins() {
  try {
    const raw = localStorage.getItem(PIN_KEY)
    if (!raw) return null
    const value = JSON.parse(raw)
    return Array.isArray(value) ? value.filter((id) => typeof id === 'string') : null
  } catch {
    return null
  }
}

export function SubjectPicker({ value, label, groups, top, onPick }) {
  const [open, setOpen] = useState(false)
  const [all, setAll] = useState(false)
  const [cat, setCat] = useState('')
  const [q, setQ] = useState('')
  const [pins, setPins] = useState(() => loadPins() ?? top.map(([id]) => id))
  const [pos, setPos] = useState(null)
  const triggerRef = useRef(null)
  const activeRef = useRef(null)
  const bodyRef = useRef(null)

  const rows = useMemo(() => groups.flatMap(([, list]) => list), [groups])
  const rowById = useMemo(() => new Map(rows.map((row) => [row[0], row])), [rows])
  const active = rows.find(([id]) => id === value)
  const pinned = useMemo(() => pins.map((id) => rowById.get(id)).filter(Boolean), [pins, rowById])
  const quick = pinned
  const ordered = useMemo(() => groups.map(([name, list]) => [
    name,
    [...list].sort((a, b) => a[1].localeCompare(b[1], undefined, { sensitivity: 'base' })),
  ]), [groups])

  const query = q.trim().toLowerCase()
  const filtered = ordered
    .map(([name, list]) => [name, list.filter(([id, text]) => !query || text.toLowerCase().includes(query) || id.includes(query))])
    .filter(([, list]) => list.length)
  const found = filtered.reduce((n, [, list]) => n + list.length, 0)
  const current = ordered.find(([name]) => name === cat)
  const currentRows = current ? current[1] : []
  const title = query ? 'Search results' : cat || 'All subjects'
  const subtitle = query ? found + (found === 1 ? ' subject' : ' subjects') : (cat ? currentRows.length : rows.length) + ' subjects'

  useEffect(() => {
    if (!open) return
    const onKey = (e) => { if (e.key === 'Escape') setOpen(false) }
    const onMove = () => setOpen(false)
    window.addEventListener('keydown', onKey)
    window.addEventListener('resize', onMove)
    window.addEventListener('scroll', onMove, true)
    return () => {
      window.removeEventListener('keydown', onKey)
      window.removeEventListener('resize', onMove)
      window.removeEventListener('scroll', onMove, true)
    }
  }, [open])

  useEffect(() => {
    if (!all) return
    const onKey = (e) => { if (e.key === 'Escape') closeAll() }
    window.addEventListener('keydown', onKey)
    const frame = requestAnimationFrame(() => activeRef.current?.scrollIntoView({ block: 'center' }))
    return () => {
      cancelAnimationFrame(frame)
      window.removeEventListener('keydown', onKey)
    }
  }, [all])

  useEffect(() => {
    if (all) bodyRef.current?.scrollTo({ top: 0 })
  }, [all, cat])

  useEffect(() => {
    try { localStorage.setItem(PIN_KEY, JSON.stringify(pins)) } catch { /* private mode */ }
  }, [pins])

  function closeAll() {
    setAll(false)
    setQ('')
    setCat('')
  }

  function toggle() {
    if (open) {
      setOpen(false)
      return
    }
    const rect = triggerRef.current.getBoundingClientRect()
    const width = Math.min(320, window.innerWidth - 24)
    setPos({
      left: Math.max(12, Math.min(rect.left, window.innerWidth - width - 12)),
      top: rect.bottom + 8,
      width,
      maxHeight: Math.max(180, window.innerHeight - rect.bottom - 24),
    })
    setOpen(true)
  }

  function pick(id) {
    closeAll()
    setOpen(false)
    if (id !== value) onPick(id)
  }

  function openAll() {
    setOpen(false)
    setAll(true)
  }

  function togglePin(id) {
    setPins((prev) => (prev.includes(id) ? prev.filter((item) => item !== id) : [id, ...prev]))
  }

  function subjectRow([id, text]) {
    const on = pins.includes(id)
    return (
      <div key={id} ref={id === value ? activeRef : null} className={'sitem' + (id === value ? ' on' : '')}>
        <button type="button" className="slabel" onClick={() => pick(id)}>
          <span>{text}</span>
          {id === value && <Check />}
        </button>
        <button type="button" className={'spin' + (on ? ' on' : '')} aria-pressed={on} aria-label={on ? 'Unpin ' + text : 'Pin ' + text} onClick={() => togglePin(id)}>
          <Pin filled={on} />
        </button>
      </div>
    )
  }

  return (
    <>
      <button ref={triggerRef} type="button" className={'spick' + (open ? ' on' : '')} aria-haspopup="listbox" aria-expanded={open} onClick={toggle}>
        <span className="stitle">{label}</span>
        <span className="schev" aria-hidden="true" />
      </button>
      {open && pos && createPortal(
        <>
          <div className="spop-scrim" onPointerDown={() => setOpen(false)} />
          <div className="spop" role="listbox" aria-label="Subject" style={pos}>
            {!quick.length && <p className="snone">No pinned subjects</p>}
            {quick.map(([id, text]) => (
              <button key={id} type="button" role="option" aria-selected={id === value} className={'srow' + (id === value ? ' on' : '')} onClick={() => pick(id)}>
                <span className="srowtext">{text}</span>
                {id === value && <Check />}
              </button>
            ))}
            <div className="sdiv" />
            <button type="button" className="srow more" onClick={openAll}>
              <span className="srowtext">More subjects…</span>
              <span className="snext" aria-hidden="true">›</span>
            </button>
          </div>
        </>,
        document.body,
      )}
      {all && createPortal(
        <div className="smodal" onMouseDown={(e) => { if (e.target === e.currentTarget) closeAll() }}>
          <div className="spanel" role="dialog" aria-modal="true" aria-label="All subjects">
            <div className="shead">
              <div className="sheadl">
                {cat && !query && (
                  <button type="button" className="sback" aria-label="All categories" onClick={() => setCat('')}>
                    <svg viewBox="0 0 16 16" aria-hidden="true">
                      <path d="M9.8 3.8 5.6 8l4.2 4.2" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </button>
                )}
                {cat && !query && (
                  <span className="sheadico" style={{ '--c': colorFor(cat) }}><CategoryIcon name={cat} /></span>
                )}
                <div>
                  <h2>{title}</h2>
                  <p>{subtitle}</p>
                </div>
              </div>
              <button type="button" className="sclose" aria-label="Close" onClick={closeAll}>
                <svg viewBox="0 0 16 16" aria-hidden="true">
                  <path d="M4 4l8 8M12 4l-8 8" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
                </svg>
              </button>
            </div>
            <label className="sfield">
              <Search />
              <input autoFocus aria-label="Search subjects" placeholder="Search all subjects" value={q} onChange={(e) => setQ(e.target.value)} />
            </label>
            <div className="sbody" ref={bodyRef}>
              {query && filtered.map(([name, list]) => (
                <section key={name} className="sgroup">
                  <h3>{name}</h3>
                  <div className="slist">{list.map(subjectRow)}</div>
                </section>
              ))}
              {!query && cat && <div className="ssubgrid">{currentRows.map(subjectRow)}</div>}
              {!query && !cat && pinned.length > 0 && (
                <section className="sgroup spinsec">
                  <h3>Pinned</h3>
                  <div className="slist">{pinned.map(subjectRow)}</div>
                </section>
              )}
              {!query && !cat && (
                <div className="scats">
                  {ordered.map(([name, list]) => (
                    <button key={name} type="button" className="scat" onClick={() => setCat(name)}>
                      <span className="scico" style={{ '--c': colorFor(name) }}><CategoryIcon name={name} /></span>
                      <span className="scname">{name}</span>
                      <span className="scn">{list.length}</span>
                      <span className="snext" aria-hidden="true">›</span>
                    </button>
                  ))}
                </div>
              )}
              {query && !filtered.length && <p className="snone">No subjects found</p>}
            </div>
          </div>
        </div>,
        document.body,
      )}
    </>
  )
}
