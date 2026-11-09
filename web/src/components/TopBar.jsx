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

function GroupIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3 3 8l9 5 9-5-9-5z" />
      <path d="m3 12 9 5 9-5" />
      <path d="m3 16 9 5 9-5" />
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

export function TopBar({ mode, query, sort, group, groups, countLabel, pills, searchRef, menuRef, onQuery, onSort, onGroup, onOpenFilters, onRemove, onClear }) {
  const sorts = mode === 'papers'
    ? [['new', 'Year, newest'], ['old', 'Year, oldest']]
    : [['new', 'Newest first'], ['old', 'Oldest first'], ['mh', 'Most marks'], ['ml', 'Fewest marks'], ['tp', 'By topic']]
  const groupLabel = groups.find(([id]) => id === group)?.[1] || groups[0][1]
  const sortLabel = sorts.find(([id]) => id === sort)?.[1] || sorts[0][1]
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
        <label className="pick">
          <GroupIcon />
          <span>{groupLabel}</span>
          <select id="group" aria-label="Group" value={group} onChange={(e) => onGroup(e.target.value)}>
            {groups.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
          </select>
        </label>
        <label className="pick">
          <SortIcon />
          <span>{sortLabel}</span>
          <select id="sort" aria-label="Sort" value={sort} onChange={(e) => onSort(e.target.value)}>
            {sorts.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
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
