import { LEVEL_ORDER, LEVELS, MARK_BANDS, SESSIONS, SUBJECTS, areaShortFor, areasFor, topicsIn } from '../bank.js'
import { Chip } from './Chip.jsx'
import { Segment } from './Segment.jsx'

function dim(count, on) {
  return !count && !on
}

export function Sidebar({
  subject,
  mode,
  questionTotal,
  paperTotal,
  onSubject,
  onMode,
  filters,
  counts,
  years,
  openAreas,
  topics,
  savedCount,
  uncategorizedCount,
  onToggle,
  onToggleArea,
  onToggleTopic,
  onToggleOpen,
  onToggleFlag,
}) {
  const questionLabel = 'Questions, ' + questionTotal
  const paperLabel = 'Whole papers, ' + paperTotal
  const papers = mode === 'papers'
  const econ = subject === 'econ'
  const leveled = subject === 'econ' || subject === 'phys'
  const areas = areasFor(subject)
  const areaShort = areaShortFor(subject)
  const paperOptions = subject === 'phys' ? [1, '1A', '1B', 2, 3] : [1, 2, 3]
  const subjectLabel = SUBJECTS.find((item) => item[0] === subject)?.[1] || SUBJECTS[0][1]
  return (
    <>
      <label className="subject">
        <h1>{subjectLabel}</h1>
        <select id="subject" aria-label="Subject" value={subject} onChange={(e) => onSubject(e.target.value)}>
          {SUBJECTS.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
        </select>
      </label>
      <label className="browse">
        <span>{papers ? paperLabel : questionLabel}</span>
        <select id="browse" aria-label="Browse" value={mode} onChange={(e) => onMode(e.target.value)}>
          {!econ && <option value="questions">{questionLabel}</option>}
          <option value="papers">{paperLabel}</option>
        </select>
      </label>
      <div className="grp">
        <h3>Paper</h3>
        <Segment
          label="Paper"
          options={paperOptions.map((paper) => ({
            value: paper,
            label: 'Paper ' + paper,
            on: filters.p.has(paper),
            dim: dim(counts.p[paper], filters.p.has(paper)),
            onClick: () => onToggle('p', paper),
          }))}
        />
      </div>
      {leveled && (
        <div className="grp">
          <h3>Level</h3>
          <div className="chips">
            {LEVEL_ORDER.filter((level) => counts.l[level] || filters.l.has(level)).map((level) => (
              <Chip key={level} on={filters.l.has(level)} dim={dim(counts.l[level], filters.l.has(level))} count={counts.l[level] || 0} onClick={() => onToggle('l', level)}>
                {LEVELS[level]}
              </Chip>
            ))}
          </div>
        </div>
      )}
      <div className="grp">
        <h3>Year</h3>
        <div className="chips">
          {years.map((year) => (
            <Chip key={year} on={filters.y.has(year)} dim={dim(counts.y[year], filters.y.has(year))} count={counts.y[year] || 0} onClick={() => onToggle('y', year)}>
              {year}
            </Chip>
          ))}
        </div>
      </div>
      <div className="grp">
        <h3>Session</h3>
        <div className="chips">
          {SESSIONS.map((session) => (
            <Chip key={session} on={filters.s.has(session)} dim={dim(counts.s[session], filters.s.has(session))} count={counts.s[session] || 0} onClick={() => onToggle('s', session)}>
              {session}
            </Chip>
          ))}
        </div>
      </div>
      {!papers && (
        <>
          <div className="grp">
            <h3>Marks</h3>
            <Segment
              label="Marks"
              options={MARK_BANDS.map((band, index) => ({
                value: index,
                label: band[0],
                on: filters.m.has(index),
                dim: dim(counts.m[index], filters.m.has(index)),
                onClick: () => onToggle('m', index),
              }))}
            />
          </div>
          <div className="grp">
            <h3>Topic</h3>
            {Object.keys(areas).map((area) => (
              <div key={area} className="area" style={{ '--c': areas[area] }}>
                <div className="arow-w">
                  <button type="button" className={'arow' + (filters.a.has(area) ? ' on' : '')} onClick={() => onToggleArea(area)}>
                    <i className="dot" />
                    {areaShort[area] || area}
                    <span className="n">{counts.a[area] || 0}</span>
                  </button>
                  <button type="button" className={'chev' + (openAreas.has(area) ? ' open' : '')} aria-label="Show topics" onClick={() => onToggleOpen(area)}>›</button>
                </div>
                {openAreas.has(area) && (
                  <div className="trows">
                    {topicsIn(topics, area).map((code) => (
                      <button
                        key={code}
                        type="button"
                        className={'trow' + (filters.t.has(code) ? ' on' : '') + (dim(counts.t[code], filters.t.has(code)) ? ' z' : '')}
                        onClick={() => onToggleTopic(code)}
                      >
                        <b>{code}</b>
                        {topics[code][0]}
                        <span className="n">{counts.t[code] || 0}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
          <div className="grp">
            <h3>Show</h3>
            <div className="chips">
              <Chip on={filters.saved} count={savedCount} onClick={() => onToggleFlag('saved')}>★ Saved</Chip>
              <Chip on={filters.ver} onClick={() => onToggleFlag('ver')}>Verified topics only</Chip>
              <Chip on={filters.unc} count={uncategorizedCount} onClick={() => onToggleFlag('unc')}>Uncategorized</Chip>
            </div>
          </div>
        </>
      )}
    </>
  )
}
