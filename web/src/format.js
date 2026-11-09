function esc(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

export function fmt(t, lim) {
  const M = [], TB = []
  t = t.replace(/\$\$[\s\S]+?\$\$|\\\[[\s\S]+?\\\]|\\\([\s\S]+?\\\)|\$[^$\n]+?\$/g, m => (M.push(m), '\u0001' + (M.length - 1) + '\u0002'))
  t = t.replace(/<table[\s\S]*?<\/table>/gi, m => { m = m.replace(/<(?!\/?(table|thead|tbody|tr|td|th)\b)[^>]*>/gi, '').replace(/<(td|th)\b([^>]*)>/gi, (x, g, a) => { const k = (a.match(/(colspan|rowspan)="?\d+"?/gi) || []).join(' '); return '<' + g + (k ? ' ' + k : '') + '>' }).replace(/<table[^>]*>/i, '<table>'); TB.push(m); return '\u0003' + (TB.length - 1) + '\u0004' })
  t = t.replace(/<\/?div[^>]*>/gi, '').replace(/^#+\s*/gm, '')
  const pipe = l => /^\s*\|.+\|/.test(l)
  const sep = l => pipe(l) && l.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').every(c => /^\s*:?-{3,}:?\s*$/.test(c))
  const cells = l => l.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(c => esc(c.trim()))
  const src = t.split('\n'), kept = []
  for (let i = 0; i < src.length;) {
    let j = i + 1
    while (j < src.length && !src[j].trim()) j++
    if (pipe(src[i]) && j < src.length && sep(src[j])) {
      const rows = [src[i]]
      i = j + 1
      while (i < src.length) {
        if (!src[i].trim()) {
          let k = i + 1
          while (k < src.length && !src[k].trim()) k++
          if (k < src.length && pipe(src[k]) && !sep(src[k])) { i = k; continue }
          break
        }
        if (pipe(src[i]) && !sep(src[i])) { rows.push(src[i++]); continue }
        break
      }
      TB.push('<table><thead><tr>' + cells(rows[0]).map(c => '<th>' + c + '</th>').join('') + '</tr></thead><tbody>' + rows.slice(1).map(r => '<tr>' + cells(r).map(c => '<td>' + c + '</td>').join('') + '</tr>').join('') + '</tbody></table>')
      kept.push('\u0003' + (TB.length - 1) + '\u0004')
    } else kept.push(src[i++])
  }
  t = kept.join('\n')
  const back = s => s.replace(/\u0001(\d+)\u0002/g, (x, i) => esc(M[i]))
  let out = '', n = 0
  for (let l of t.split('\n')) {
    l = l.trim()
    if (!l) continue
    let h, r
    if (r = l.match(/^!\[\]\((\/fig\/[a-z0-9-]+\.png)\)$/)) h = '<img class="fig" alt="Diagram" src="' + r[1] + '">'
    else if (r = l.match(/^\u0003(\d+)\u0004$/)) h = '<div class="tw">' + TB[r[1]].replace(/\u0001(\d+)\u0002/g, (x, i) => esc(M[i])) + '</div>'
    else if (r = l.match(/^\[(\d+)\]$/)) h = '<div class="pm"><span class="pts" title="' + r[1] + (r[1] === '1' ? ' mark' : ' marks') + '">' + r[1] + '</span></div>'
    else {
      const mk = l.match(/\s*\[(\d+)\]$/), mv = mk && !/maximum mark/i.test(l) ? mk[1] : ''
      if (mv) l = l.slice(0, mk.index).trimEnd()
      l = esc(l)
      const b = mv ? '<span class="pts" title="' + mv + (mv === '1' ? ' mark' : ' marks') + '">' + mv + '</span>' : ''
      h = (r = l.match(/^(\((?:[a-h]|i{1,3}|iv|vi{0,3}|ix|x)\))\s+([\s\S]*)$/)) ? '<p class="pt"><b>' + r[1] + '</b><span>' + back(r[2]) + '</span>' + b + '</p>' : '<p' + (b ? ' class="ln"' : '') + '>' + back(l) + b + '</p>'
    }
    out += h
    n += l.length
    if (lim && n > lim) break
  }
  return out
}
