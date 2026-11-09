export function filtersFrom(search) {
  const u = new URLSearchParams(search), F = { p: new Set(), y: new Set(), s: new Set(), m: new Set(), a: new Set(), t: new Set(), saved: false, ver: false, q: '', sort: 'new' }
  for (const k of ['p', 'y', 's', 'm', 'a', 't']) for (const x of (u.get(k) || '').split(',')) {
    if (!x) continue
    if (k === 'p' || k === 'y' || k === 'm') { const n = +x; if (Number.isFinite(n)) F[k].add(n) }
    else F[k].add(x)
  }
  F.saved = u.get('saved') === '1'
  F.ver = u.get('ver') === '1'
  F.q = u.get('q') || ''
  const sort = u.get('sort')
  if (['old', 'mh', 'ml', 'tp'].includes(sort)) F.sort = sort
  F.browse = u.get('browse') === 'papers' ? 'papers' : 'questions'
  return F
}

export function filtersTo(S, q, sort, path) {
  const u = new URLSearchParams()
  for (const k of ['p', 'y', 's', 'm', 'a', 't']) if (S[k].size) u.set(k, [...S[k]].join(','))
  if (S.saved) u.set('saved', '1')
  if (S.ver) u.set('ver', '1')
  if (q) u.set('q', q)
  if (sort && sort !== 'new') u.set('sort', sort)
  if (S.browse === 'papers') u.set('browse', 'papers')
  const s = u.toString()
  return s ? path + '?' + s : path
}
