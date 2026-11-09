import { AREA_SHORT } from './areas.js'

export const MARK_BANDS = [
  ['1–5', (m) => m <= 5],
  ['6–9', (m) => m >= 6 && m <= 9],
  ['10–14', (m) => m >= 10 && m <= 14],
  ['15+', (m) => m >= 15],
]

export const SESSIONS = ['May', 'November', 'Specimen']

const WHEN = { May: 0, November: 1, Specimen: 2 }

export function label(q) {
  return (q.s === 'Specimen' ? 'Specimen ' : q.s + ' ') + q.y
}

export function paperName(p) {
  return p.s + ' ' + p.y + ', Paper ' + p.p + (p.z ? ', ' + p.z : '')
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
  if (skip !== 'p' && S.p.size && !S.p.has(p.p)) return false
  if (skip !== 'y' && S.y.size && !S.y.has(p.y)) return false
  if (skip !== 's' && S.s.size && !S.s.has(p.s)) return false
  if (txt) for (const w of txt.split(/\s+/)) if (w && !paperHay(p).includes(w)) return false
  return true
}

function paperHay(p) {
  return (p.s + ' ' + p.y + ' paper ' + p.p + ' ' + (p.z || '')).toLowerCase()
}

export function tally(items, ok, fn) {
  const counts = {}
  for (const item of items) {
    if (!ok(item)) continue
    for (const key of fn(item)) counts[key] = (counts[key] || 0) + 1
  }
  return counts
}

export function sortQuestions(list, key) {
  const cmp = {
    new: () => 0,
    old: (a, b) => b.ord - a.ord,
    mh: (a, b) => (b.m || 0) - (a.m || 0),
    ml: (a, b) => (a.m ?? 99) - (b.m ?? 99),
    tp: (a, b) => (a.c[0] || '').localeCompare(b.c[0] || '', undefined, { numeric: true }),
  }[key] || (() => 0)
  return [...list].sort(cmp)
}

export function sortPapers(list, sort) {
  const old = sort === 'old'
  return [...list].sort((a, b) => {
    const d = (a.y - b.y) || ((WHEN[a.s] ?? 9) - (WHEN[b.s] ?? 9))
    return (d ? (old ? d : -d) : 0) || a.p - b.p || (a.z || '').localeCompare(b.z || '')
  })
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
