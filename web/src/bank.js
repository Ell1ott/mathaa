import { AREAS, AREA_SHORT } from './areas.js'

export const MARK_BANDS = [
  ['1–5', (m) => m <= 5],
  ['6–9', (m) => m >= 6 && m <= 9],
  ['10–14', (m) => m >= 10 && m <= 14],
  ['15+', (m) => m >= 15],
]

export const SESSIONS = ['May', 'November', 'Specimen']

export const SUBJECTS = [
  ['math', 'IB Math AA HL'],
  ['econ', 'IB Economics'],
]

export const LEVELS = { hl: 'HL', sl: 'SL', hlsl: 'HL & SL', na: 'Other' }
export const LEVEL_ORDER = ['hl', 'sl', 'hlsl', 'na']

const WHEN = { May: 0, November: 1, Specimen: 2 }

export function label(q) {
  return (q.s === 'Specimen' ? 'Specimen ' : q.s + ' ') + q.y
}

export function paperName(p) {
  const level = p.l ? (LEVELS[p.l] || p.l) + ' ' : ''
  return level + p.s + ' ' + p.y + ', Paper ' + p.p + (p.z ? ', ' + p.z : '')
}

export function calculator(q) {
  return q.p === 1 ? 'No calculator' : 'Calculator allowed'
}

export function prepare(data) {
  const topics = data.topics || {}
  const questions = (data.qs || []).map((q, ord) => ({
    ...q,
    ord,
    ar: [...new Set((q.c || []).map((c) => topics[c]?.[1]).filter(Boolean))],
    h: (q.t + ' ' + label(q) + ' paper ' + q.p + ' ' + (q.z || '') + ' q' + q.n + ' ' + (q.c || []).map((c) => c + ' ' + (topics[c]?.[0] || '')).join(' ')).toLowerCase(),
  }))
  const papers = []
  const byId = new Map()
  for (const q of questions) {
    const i = q.i.replace(/-q\d+$/, '')
    let paper = byId.get(i)
    if (!paper) {
      paper = { i, y: q.y, s: q.s, p: q.p, z: q.z || '', n: 0 }
      byId.set(i, paper)
      papers.push(paper)
    }
    paper.n++
  }
  for (const p of data.ps || []) {
    papers.push({ i: p.i, y: p.y, s: p.s, p: p.p, z: p.z || '', n: 0, l: p.l || '', u: 'econ' })
  }
  return { topics, questions, papers }
}

export function toggleSet(set, value) {
  const next = new Set(set)
  if (next.has(value)) next.delete(value)
  else next.add(value)
  return next
}

export function matchesQuestion(q, S, stars, skip, txt) {
  if (skip !== 'p' && S.p.size && !S.p.has(q.p)) return false
  if (skip !== 'y' && S.y.size && !S.y.has(q.y)) return false
  if (skip !== 's' && S.s.size && !S.s.has(q.s)) return false
  if (skip !== 'm' && S.m.size && !(q.m != null && [...S.m].some((i) => MARK_BANDS[i][1](q.m)))) return false
  if (skip !== 't' && (S.t.size || S.a.size) && !(q.c.some((c) => S.t.has(c)) || q.ar.some((a) => S.a.has(a)))) return false
  if (S.saved && !stars[q.i]) return false
  if (S.ver && !q.v) return false
  if (txt) for (const w of txt.split(/\s+/)) if (w && !q.h.includes(w)) return false
  return true
}

export function matchesPaper(p, S, skip, txt) {
  if ((S.sub || 'math') !== (p.u || 'math')) return false
  if (skip !== 'p' && S.p.size && !S.p.has(p.p)) return false
  if (skip !== 'y' && S.y.size && !S.y.has(p.y)) return false
  if (skip !== 's' && S.s.size && !S.s.has(p.s)) return false
  if (skip !== 'l' && S.l.size && p.l && !S.l.has(p.l)) return false
  if (txt) for (const w of txt.split(/\s+/)) if (w && !paperHay(p).includes(w)) return false
  return true
}

function paperHay(p) {
  const level = p.l === 'hlsl' ? 'hl sl' : (p.l || '')
  return (level + ' ' + p.s + ' ' + p.y + ' paper ' + p.p + ' ' + (p.z || '')).toLowerCase()
}

export function tally(items, ok, fn) {
  const counts = {}
  for (const item of items) {
    if (!ok(item)) continue
    for (const key of fn(item)) counts[key] = (counts[key] || 0) + 1
  }
  return counts
}

const QUESTION_GROUPS = [
  ['sub', 'Subtopic'],
  ['area', 'Topic'],
  ['year', 'Year'],
  ['paper', 'Paper'],
  ['session', 'Session'],
]

const PAPER_GROUPS = [
  ['year', 'Year'],
  ['session', 'Session'],
  ['paper', 'Paper'],
  ['level', 'Level'],
]

const AREA_INDEX = Object.fromEntries(Object.keys(AREAS).map((name, i) => [name, i]))

export function groupOptions(mode, subject) {
  if (mode !== 'papers') return QUESTION_GROUPS
  return subject === 'econ' ? PAPER_GROUPS : PAPER_GROUPS.filter(([id]) => id !== 'level')
}

export function defaultGroup(mode) {
  return mode === 'papers' ? 'year' : 'sub'
}

export function resolveGroup(mode, subject, group) {
  const ids = groupOptions(mode, subject).map(([id]) => id)
  return ids.includes(group) ? group : defaultGroup(mode)
}

function questionCmp(sort) {
  return {
    new: () => 0,
    old: (a, b) => b.ord - a.ord,
    mh: (a, b) => (b.m || 0) - (a.m || 0),
    ml: (a, b) => (a.m ?? 99) - (b.m ?? 99),
    tp: (a, b) => (a.c[0] || '').localeCompare(b.c[0] || '', undefined, { numeric: true }),
  }[sort] || (() => 0)
}

function paperCmp(sort) {
  const old = sort === 'old'
  return (a, b) => {
    const d = (a.y - b.y) || ((WHEN[a.s] ?? 9) - (WHEN[b.s] ?? 9))
    return (d ? (old ? d : -d) : 0) || a.p - b.p || (a.z || '').localeCompare(b.z || '') || (a.l || '').localeCompare(b.l || '')
  }
}

function cmpList(a, b) {
  const n = Math.max(a.length, b.length)
  for (let i = 0; i < n; i++) {
    const d = (a[i] ?? 0) - (b[i] ?? 0)
    if (d) return d
  }
  return 0
}

function codeRank(code) {
  const [major, minor] = String(code).split('.')
  return (Number(major) || 0) * 1000 + (Number(minor) || 0)
}

function questionRank(q, group, sort, topics) {
  if (group === 'year') return [sort === 'old' ? q.y : -q.y]
  if (group === 'paper') return [q.p]
  if (group === 'session') return [WHEN[q.s] ?? 9]
  if (group === 'area') {
    const area = q.ar[0] || ''
    return [area in AREA_INDEX ? AREA_INDEX[area] : 99]
  }
  const code = q.c[0] || ''
  if (!code) return [99, 99]
  const area = topics[code]?.[1] || ''
  return [area in AREA_INDEX ? AREA_INDEX[area] : 98, codeRank(code)]
}

function paperRank(p, group, sort) {
  if (group === 'year') return [sort === 'old' ? p.y : -p.y]
  if (group === 'session') return [WHEN[p.s] ?? 9]
  if (group === 'paper') return [p.p]
  const level = LEVEL_ORDER.indexOf(p.l)
  return [level < 0 ? 99 : level]
}

export function sortQuestions(list, key) {
  return [...list].sort(questionCmp(key))
}

export function sortPapers(list, sort) {
  return [...list].sort(paperCmp(sort))
}

export function orderQuestions(list, group, sort, topics) {
  const key = resolveGroup('questions', 'math', group)
  return [...list].sort((a, b) => cmpList(questionRank(a, key, sort, topics), questionRank(b, key, sort, topics)) || questionCmp(sort)(a, b))
}

export function orderPapers(list, group, sort, subject) {
  const key = resolveGroup('papers', subject, group)
  return [...list].sort((a, b) => cmpList(paperRank(a, key, sort), paperRank(b, key, sort)) || paperCmp(sort)(a, b))
}

// shortcut: first topic only, duplicate a question into each subtopic if cross-listed ones should show twice
export function questionBucket(q, group, topics) {
  if (group === 'year') return { id: 'y' + q.y, label: String(q.y) }
  if (group === 'paper') return { id: 'p' + q.p, label: 'Paper ' + q.p }
  if (group === 'session') return { id: 's' + q.s, label: q.s }
  if (group === 'area') {
    const area = q.ar[0] || ''
    return { id: 'a' + area, label: area || 'Other' }
  }
  const code = q.c[0] || ''
  if (!code) return { id: 'sub', label: 'Other' }
  return { id: 'sub' + code, label: topics[code]?.[0] || code, code }
}

export function paperBucket(p, group) {
  if (group === 'year') return { id: 'y' + p.y, label: String(p.y) }
  if (group === 'session') return { id: 's' + p.s, label: p.s }
  if (group === 'paper') return { id: 'p' + p.p, label: 'Paper ' + p.p }
  return { id: 'l' + (p.l || ''), label: LEVELS[p.l] || 'Other' }
}

export function chunk(items, bucketOf) {
  const groups = []
  for (let i = 0; i < items.length; i++) {
    const bucket = bucketOf(items[i])
    const last = groups[groups.length - 1]
    if (last && last.id === bucket.id) last.rows.push({ item: items[i], i })
    else groups.push({ id: bucket.id, label: bucket.label, code: bucket.code || '', rows: [{ item: items[i], i }] })
  }
  return groups
}

export function topicsIn(topics, area) {
  return Object.keys(topics)
    .filter((code) => topics[code][1] === area)
    .sort((a, b) => parseFloat(a.split('.')[1]) - parseFloat(b.split('.')[1]))
}

export function activePills(S, topics, query) {
  const pills = []
  const push = (group, value, label) => pills.push({ id: group + ':' + value, group, value, label })
  S.p.forEach((v) => push('p', v, 'Paper ' + v))
  S.y.forEach((v) => push('y', v, String(v)))
  S.s.forEach((v) => push('s', v, v))
  if (S.sub === 'econ') S.l.forEach((v) => push('l', v, LEVELS[v] || v))
  if (S.browse !== 'papers') {
    S.m.forEach((v) => push('m', v, MARK_BANDS[v][0] + ' marks'))
    S.a.forEach((v) => push('a', v, AREA_SHORT[v] || v))
    S.t.forEach((v) => push('t', v, topics[v]?.[0] || v))
    if (S.saved) push('f', 'saved', 'Saved')
    if (S.ver) push('f', 'ver', 'Verified topics')
  }
  if (query) push('x', '', '“' + query + '”')
  return pills
}

export function yearsOf(items) {
  return [...new Set(items.map((item) => item.y))].sort((a, b) => b - a)
}
