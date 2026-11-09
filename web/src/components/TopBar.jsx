import { PillRow } from './Pill.jsx'

function FilterIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="m3 16 4 4 4-4" />
      <path d="M7 20V4" />
      <path d="M11 4h10" />
      <path d="M11 8h7" />
      <path d="M11 12h4" />
    </svg>
  )
}

function SortIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="m21 16-4 4-4-4" />
      <path d="M17 20V4" />
      <path d="m3 8 4-4 4 4" />
      <path d="M7 4v16" />
    </svg>
  )
}

export function TopBar({ mode, query, sort, countLabel, pills, searchRef, menuRef, onQuery, onSort, onOpenFilters, onRemove, onClear }) {
  return (
    <div className="top">
      <div className="bar">
        <button type="button" className="fbtn" id="fopen" aria-label="Filters" onClick={onOpenFilters}>
          <FilterIcon />
          <span className="flab">Filters</span>
          <span id="fbadge">{pills.length || ''}</span>
        </button>
        <label className="search">
          <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
            <circle cx="7" cy="7" r="5" />
            <path d="m11 11 3.5 3.5" />
          </svg>
          <input
            ref={searchRef}
            id="q"
            type="search"
            placeholder={mode === 'papers' ? 'Search year, session, time zone' : 'Search questions, topics, papers'}
            autoComplete="off"
            aria-label="Search"
            value={query}
            onChange={(e) => onQuery(e.target.value)}
          />
          <kbd>/</kbd>
        </label>
        <label className="sortbtn">
          <SortIcon />
          <select id="sort" aria-label="Sort" value={sort} onChange={(e) => onSort(e.target.value)}>
            {mode === 'papers' ? (
              <>
                <option value="new">Year, newest</option>
                <option value="old">Year, oldest</option>
              </>
            ) : (
              <>
                <option value="new">Newest first</option>
                <option value="old">Oldest first</option>
                <option value="mh">Most marks</option>
                <option value="ml">Fewest marks</option>
                <option value="tp">By topic</option>
              </>
            )}
          </select>
        </label>
      </div>
      <div className="meta" id="meta">
        <span className="count">{countLabel}</span>
        {pills.length > 0 && (
          <>
            <PillRow pills={pills} onRemove={onRemove} menuRef={menuRef} />
            <button type="button" className="clear" onClick={onClear}>Clear all</button>
          </>
        )}
      </div>
    </div>
  )
}
