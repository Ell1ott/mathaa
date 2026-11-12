import { defaultGroup, resolveGroup } from './bank.js'

export function filtersFrom(search) {
  const u = new URLSearchParams(search), F = { p: new Set(), y: new Set(), s: new Set(), m: new Set(), a: new Set(), t: new Set(), l: new Set(), saved: false, ver: false, unc: false, q: '', sort: 'new', sub: 'math' }
  for (const k of ['p', 'y', 's', 'm', 'a', 't', 'l']) for (const x of (u.get(k) || '').split(',')) {
    if (!x) continue
    if (k === 'p' && /^\d+[A-Za-z]$/.test(x)) { F.p.add(x.toUpperCase()); continue }
    if (k === 'p' || k === 'y' || k === 'm') { const n = +x; if (Number.isFinite(n)) F[k].add(n) }
    else F[k].add(x)
  }
  F.saved = u.get('saved') === '1'
  F.ver = u.get('ver') === '1'
  F.unc = u.get('unc') === '1'
  F.q = u.get('q') || ''
  const sort = u.get('sort')
  if (['old', 'mh', 'ml', 'tp'].includes(sort)) F.sort = sort
  F.browse = u.get('browse') === 'papers' ? 'papers' : 'questions'
  F.sub = u.get('sub') === 'econ' ? 'econ' : u.get('sub') === 'phys' ? 'phys' : 'math'
  if (F.sub === 'econ') F.browse = 'papers'
  F.group = resolveGroup(F.browse, F.sub, u.get('g') || '')
  return F
}

export function filtersTo(S, q, sort, path, open) {
  const u = new URLSearchParams()
  for (const k of ['p', 'y', 's', 'm', 'a', 't', 'l']) if (S[k]?.size) u.set(k, [...S[k]].join(','))
  if (S.sub === 'econ' || S.sub === 'phys') u.set('sub', S.sub)
  if (S.saved) u.set('saved', '1')
  if (S.ver) u.set('ver', '1')
  if (S.unc) u.set('unc', '1')
  if (q) u.set('q', q)
  if (sort && sort !== 'new') u.set('sort', sort)
  if (S.browse === 'papers') u.set('browse', 'papers')
  if (S.group && S.group !== defaultGroup(S.browse || 'questions')) u.set('g', S.group)
  if (open) u.set('open', open)
  const s = u.toString()
  return s ? path + '?' + s : path
}
