import { useEffect, useMemo, useRef, useState } from 'react'
import { filtersFrom, filtersTo } from './filters.js'
import {
  MARK_BANDS,
  activePills,
  chunk,
  groupOptions,
  matchesPaper,
  matchesQuestion,
  orderPapers,
  orderQuestions,
  paperBucket,
  prepare,
  questionBucket,
  resolveGroup,
  tally,
  toggleSet,
  yearsOf,
} from './bank.js'
import { Empty } from './components/Empty.jsx'
import { PaperRow } from './components/PaperRow.jsx'
import { QuestionCard } from './components/QuestionCard.jsx'
import { QuestionSheet } from './components/QuestionSheet.jsx'
import { Sidebar } from './components/Sidebar.jsx'
import { TopBar } from './components/TopBar.jsx'

const STAR_KEY = 'ibq-star'

function loadStars() {
  try { return JSON.parse(localStorage.getItem(STAR_KEY) || '{}') } catch { return {} }
}

function saveStars(stars) {
  try { localStorage.setItem(STAR_KEY, JSON.stringify(stars)) } catch { /* private mode */ }
}

function initialFilters() {
  const filters = filtersFrom(location.search)
  if ((filters.browse === 'papers' || filters.sub === 'econ') && !['new', 'old'].includes(filters.sort)) filters.sort = 'new'
  return filters
}

function countLabel(n, total, noun) {
  return n + ' of ' + total + ' ' + (total === 1 ? noun : noun + 's')
}

function Sections({ groups, limit, scope, render }) {
  const [closed, setClosed] = useState(() => new Set())
  const nodes = []
  let left = limit
  for (const group of groups) {
    if (left <= 0) break
    const key = scope + '\0' + group.id
    const open = !closed.has(key)
    const take = open ? group.rows.slice(0, left) : []
    if (open) left -= take.length
    nodes.push(
      <h2 className="ghead" key={'g-' + group.id}>
        <button
          type="button"
          aria-expanded={open}
          onClick={() => setClosed((prev) => {
            const next = new Set(prev)
            if (next.has(key)) next.delete(key)
            else next.add(key)
            return next
          })}
        >
          <span className={'chev' + (open ? ' open' : '')} aria-hidden="true">›</span>
          {group.code ? <span className="gc">{group.code}</span> : null}
          <span>{group.label}</span>
          <span className="gn">{group.rows.length}</span>
        </button>
      </h2>,
    )
    for (const row of take) nodes.push(render(row))
  }
  return nodes
}

export default function App() {
  const [bank, setBank] = useState(null)
  const [error, setError] = useState('')
  const [filters, setFilters] = useState(initialFilters)
  const [query, setQuery] = useState(() => initialFilters().q)
  const [txt, setTxt] = useState(() => initialFilters().q.trim().toLowerCase())
  const [stars, setStars] = useState(loadStars)
  const [openAreas, setOpenAreas] = useState(() => new Set(initialFilters().a))
  const [shown, setShown] = useState(30)
  const [sideOpen, setSideOpen] = useState(false)
  const [sheet, setSheet] = useState({ open: false, docs: false, index: 0, view: 'text' })
  const [copied, setCopied] = useState(false)
  const mainRef = useRef(null)
  const searchRef = useRef(null)
  const sentRef = useRef(null)
  const menuRef = useRef({})
  const scrollRef = useRef(false)
  const seeded = useRef(false)
  const lenRef = useRef(0)

  useEffect(() => {
    let gone = false
    fetch('/questions.json')
      .then((res) => {
        if (!res.ok) throw new Error('Could not load questions')
        return res.json()
      })
      .then((data) => { if (!gone) setBank(prepare(data)) })
      .catch((err) => { if (!gone) setError(err.message) })
    return () => { gone = true }
  }, [])

  useEffect(() => {
    if (!bank || seeded.current) return
    seeded.current = true
    setOpenAreas((prev) => {
      const next = new Set(prev)
      filters.t.forEach((code) => { if (bank.topics[code]) next.add(bank.topics[code][1]) })
      return next
    })
  }, [bank, filters.t])

  useEffect(() => {
    const timer = setTimeout(() => {
      setTxt(query.trim().toLowerCase())
      setShown(30)
      scrollRef.current = true
    }, 140)
    return () => clearTimeout(timer)
  }, [query])

  useEffect(() => {
    history.replaceState(null, '', filtersTo(filters, query.trim(), filters.sort, location.pathname))
  }, [filters, txt])

  useEffect(() => {
    if (!scrollRef.current || !mainRef.current) return
    mainRef.current.scrollTop = 0
    scrollRef.current = false
  })

  const questions = useMemo(() => {
    if (!bank) return []
    const matched = bank.questions.filter((q) => matchesQuestion(q, filters, stars, null, txt))
    return orderQuestions(matched, filters.group, filters.sort, bank.topics)
  }, [bank, filters, stars, txt])

  const subjectPapers = useMemo(() => {
    if (!bank) return []
    const sub = filters.sub || 'math'
    return bank.papers.filter((p) => (p.u || 'math') === sub)
  }, [bank, filters.sub])

  const papers = useMemo(() => {
    const matched = subjectPapers.filter((p) => matchesPaper(p, filters, null, txt))
    return orderPapers(matched, filters.group, filters.sort, filters.sub)
  }, [subjectPapers, filters, txt])

  lenRef.current = questions.length

  useEffect(() => {
    const el = sentRef.current
    if (!el) return undefined
    const io = new IntersectionObserver((entries) => {
      if (!entries[0].isIntersecting) return
      setShown((n) => (n >= lenRef.current ? n : n + 30))
    }, { rootMargin: '600px' })
    io.observe(el)
    return () => io.disconnect()
  }, [bank])

  useEffect(() => {
    if (!sheet.open || sheet.docs) return
    if (sheet.index >= questions.length) {
      setSheet((s) => ({ ...s, index: Math.max(0, questions.length - 1), open: questions.length > 0 }))
    }
  }, [questions.length, sheet.open, sheet.docs, sheet.index])

  useEffect(() => {
    function onKey(e) {
      const typing = document.activeElement && /INPUT|SELECT/.test(document.activeElement.tagName)
      if (e.key === 'Escape') {
        if (menuRef.current.isOpen?.()) { menuRef.current.close(); return }
        if (sheet.open) { setSheet((s) => ({ ...s, open: false, docs: false })); setSideOpen(false); return }
        if (typing) document.activeElement.blur()
        else setSideOpen(false)
        return
      }
      if (e.key === '/' && !typing) { e.preventDefault(); searchRef.current?.focus(); return }
      if (typing || !sheet.open) return
      const list = sheet.docs ? papers : questions
      if (e.key === 'ArrowRight') step(1, list)
      if (e.key === 'ArrowLeft') step(-1, list)
      if (!sheet.docs && (e.key === 's' || e.key === 'b')) toggleStar(questions[sheet.index]?.i)
    }
    function step(delta, list) {
      const next = sheet.index + delta
      if (next < 0 || next >= list.length) return
      openIndex(next, sheet.docs)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  })

  function requestScroll() { scrollRef.current = true }

  function resetList() {
    setShown(30)
    requestScroll()
  }

  function onSubject(sub) {
    setFilters((S) => {
      const econ = sub === 'econ'
      const browse = econ ? 'papers' : S.browse
      const sort = econ && !['new', 'old'].includes(S.sort) ? 'new' : S.sort
      return { ...S, sub, browse, sort, group: resolveGroup(browse, sub, S.group), l: new Set() }
    })
    setSheet((s) => ({ ...s, open: false, docs: false }))
    resetList()
  }

  function onMode(browse) {
    setFilters((S) => {
      if (S.sub === 'econ' && browse !== 'papers') return S
      const sort = browse === 'papers' && !['new', 'old'].includes(S.sort) ? 'new' : S.sort
      return { ...S, browse, sort, group: resolveGroup(browse, S.sub, S.group) }
    })
    setSheet((s) => ({ ...s, open: false, docs: false }))
    resetList()
  }

  function onToggle(group, value) {
    setFilters((S) => ({ ...S, [group]: toggleSet(S[group], value) }))
    resetList()
  }

  function onToggleArea(area) {
    setFilters((S) => {
      const a = toggleSet(S.a, area)
      if (a.has(area)) setOpenAreas((prev) => new Set(prev).add(area))
      return { ...S, a }
    })
    resetList()
  }

  function onToggleTopic(code) {
    setFilters((S) => ({ ...S, t: toggleSet(S.t, code) }))
    resetList()
  }

  function onToggleOpen(area) {
    setOpenAreas((prev) => toggleSet(prev, area))
  }

  function onToggleFlag(flag) {
    setFilters((S) => ({ ...S, [flag]: !S[flag] }))
    resetList()
  }

  function onSort(sort) {
    setFilters((S) => ({ ...S, sort }))
    setShown(30)
  }

  function onGroup(group) {
    setFilters((S) => ({ ...S, group: resolveGroup(S.browse, S.sub, group) }))
    resetList()
  }

  function onQuery(value) {
    setQuery(value)
  }

  function clearAll() {
    setFilters((S) => ({
      ...S,
      p: new Set(), y: new Set(), s: new Set(), m: new Set(), a: new Set(), t: new Set(), l: new Set(),
      saved: false, ver: false,
    }))
    setQuery('')
    setTxt('')
    resetList()
  }

  function removePill(pill) {
    if (pill.group === 'x') { setQuery(''); setTxt(''); resetList(); return }
    if (pill.group === 'f') { onToggleFlag(pill.value); return }
    onToggle(pill.group, pill.value)
  }

  function toggleStar(id) {
    if (!id) return
    setStars((prev) => {
      const next = { ...prev }
      if (next[id]) delete next[id]
      else next[id] = 1
      saveStars(next)
      return next
    })
    if (filters.saved) resetList()
  }

  function openIndex(index, docs) {
    const list = docs ? papers : questions
    if (index < 0 || index >= list.length) return
    if (docs) {
      setSheet((s) => ({ ...s, open: true, docs: true, index }))
      return
    }
    setShown((n) => (index >= n ? index + 10 : n))
    setSheet((s) => {
      const q = questions[index]
      const view = s.view === 'scheme' && q && !q.k ? 'text' : s.view
      return { open: true, docs: false, index, view }
    })
  }

  function onView(view) {
    if (view === 'scheme' && !questions[sheet.index]?.k) return
    setSheet((s) => ({ ...s, view }))
  }

  function copyQuestion() {
    const q = questions[sheet.index]
    if (!q || !navigator.clipboard) return
    navigator.clipboard.writeText(q.t).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 900)
    }).catch(() => {})
  }

  if (!bank) {
    return (
      <div className="empty">
        <b>{error || 'Loading questions'}</b>
        {error && 'Start python scripts/serve.py, then reload.'}
      </div>
    )
  }

  const papersMode = filters.browse === 'papers'
  const qCounts = {
    p: tally(bank.questions, (q) => matchesQuestion(q, filters, stars, 'p', txt), (q) => [q.p]),
    y: tally(bank.questions, (q) => matchesQuestion(q, filters, stars, 'y', txt), (q) => [q.y]),
    s: tally(bank.questions, (q) => matchesQuestion(q, filters, stars, 's', txt), (q) => [q.s]),
    m: tally(bank.questions, (q) => matchesQuestion(q, filters, stars, 'm', txt), (q) => (
      q.m == null ? [] : MARK_BANDS.map((band, i) => (band[1](q.m) ? i : -1)).filter((i) => i >= 0)
    )),
    t: tally(bank.questions, (q) => matchesQuestion(q, filters, stars, 't', txt), (q) => q.c),
    a: tally(bank.questions, (q) => matchesQuestion(q, filters, stars, 't', txt), (q) => q.ar),
  }
  const pCounts = {
    p: tally(subjectPapers, (p) => matchesPaper(p, filters, 'p', txt), (p) => [p.p]),
    y: tally(subjectPapers, (p) => matchesPaper(p, filters, 'y', txt), (p) => [p.y]),
    s: tally(subjectPapers, (p) => matchesPaper(p, filters, 's', txt), (p) => [p.s]),
    l: tally(subjectPapers, (p) => matchesPaper(p, filters, 'l', txt), (p) => (p.l ? [p.l] : [])),
  }
  const counts = papersMode ? pCounts : qCounts
  const years = yearsOf(papersMode ? subjectPapers : bank.questions)
  const groups = papersMode
    ? chunk(papers, (paper) => paperBucket(paper, filters.group))
    : chunk(questions, (question) => questionBucket(question, filters.group, bank.topics))
  const pills = activePills(filters, bank.topics, txt)
  const noun = papersMode ? 'paper' : 'question'
  const visible = papersMode ? papers.length : questions.length
  const total = papersMode ? bank.papers.length : bank.questions.length
  const scrim = sideOpen || sheet.open

  return (
    <>
      <div className="app">
        <aside id="side" aria-label="Filters" className={sideOpen ? 'on' : ''}>
          <Sidebar
            subject={filters.sub}
            mode={filters.browse}
            questionTotal={bank.questions.length}
            paperTotal={subjectPapers.length}
            onSubject={onSubject}
            onMode={onMode}
            filters={filters}
            counts={counts}
            years={years}
            openAreas={openAreas}
            topics={bank.topics}
            savedCount={Object.keys(stars).length}
            onToggle={onToggle}
            onToggleArea={onToggleArea}
            onToggleTopic={onToggleTopic}
            onToggleOpen={onToggleOpen}
            onToggleFlag={onToggleFlag}
          />
        </aside>
        <main id="main" ref={mainRef}>
          <TopBar
            mode={filters.browse}
            query={query}
            sort={filters.sort}
            group={filters.group}
            groups={groupOptions(filters.browse, filters.sub)}
            countLabel={countLabel(visible, total, noun)}
            pills={pills}
            searchRef={searchRef}
            menuRef={menuRef}
            onQuery={onQuery}
            onSort={onSort}
            onGroup={onGroup}
            onOpenFilters={() => setSideOpen(true)}
            onRemove={removePill}
            onClear={clearAll}
          />
          <div className={'grid' + (papersMode ? ' list' : '')} id="grid">
            {papersMode && !papers.length && <Empty title="No papers match" onClear={clearAll}>Try another year or session.</Empty>}
            {!papersMode && !questions.length && <Empty title="No questions match" onClear={clearAll}>Try removing a filter or searching for something broader.</Empty>}
            <Sections
              groups={groups}
              limit={papersMode ? papers.length : shown}
              scope={filters.browse + filters.group}
              render={({ item, i }) => (papersMode ? (
                <PaperRow key={item.i} paper={item} onOpen={() => openIndex(i, true)} />
              ) : (
                <QuestionCard
                  key={item.i}
                  question={item}
                  topics={bank.topics}
                  saved={!!stars[item.i]}
                  onOpen={() => openIndex(i, false)}
                  onStar={() => toggleStar(item.i)}
                />
              ))}
            />
          </div>
          <div id="sent" ref={sentRef} style={{ height: 1 }} />
        </main>
      </div>
      <div className={'scrim' + (scrim ? ' on' : '')} id="scrim" onClick={() => { setSheet((s) => ({ ...s, open: false, docs: false })); setSideOpen(false) }} />
      <QuestionSheet
        open={sheet.open}
        docs={sheet.docs}
        index={sheet.index}
        view={sheet.view}
        question={questions[sheet.index]}
        questions={questions}
        paper={papers[sheet.index]}
        papers={papers}
        topics={bank.topics}
        saved={!!stars[questions[sheet.index]?.i]}
        copied={copied}
        onClose={() => { setSheet((s) => ({ ...s, open: false, docs: false })); setSideOpen(false) }}
        onIndex={(index) => openIndex(index, sheet.docs)}
        onView={onView}
        onStar={() => toggleStar(questions[sheet.index]?.i)}
        onCopy={copyQuestion}
      />
    </>
  )
}
