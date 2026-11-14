const pending = []

export function typeset(els) {
  const list = els.filter(Boolean)
  if (!list.length) return
  if (!window.mjReady) {
    pending.push(...list)
    return
  }
  window.mjq = (window.mjq || Promise.resolve())
    .then(() => window.MathJax.typesetPromise(list))
    .then(() => { for (const el of list) mark(el) })
    .catch(() => {})
}

// SVG glyphs are not text, so each formula gets a transparent selectable layer.
// The source lives in data-tex; the layer is ignored by MathJax so it is not typeset again.
function mark(root) {
  const doc = window.MathJax?.startup?.document
  if (!doc?.getMathItemsWithin) return
  for (const item of doc.getMathItemsWithin(root)) {
    const box = item.typesetRoot
    if (!box || !root.contains(box)) continue
    box.setAttribute('data-tex', item.math)
    box.setAttribute('data-display', item.display ? 'true' : 'false')
    let hit = box.querySelector(':scope > .msrc')
    if (!hit) {
      hit = document.createElement('span')
      hit.className = 'msrc tex2jax_ignore'
      hit.setAttribute('aria-hidden', 'true')
      box.appendChild(hit)
    }
    hit.textContent = item.display ? '$$\n' + item.math + '\n$$' : '$' + item.math + '$'
  }
}

function boxOf(node) {
  const el = node && (node.nodeType === 1 ? node : node.parentElement)
  return el?.closest?.('mjx-container') || null
}

function textOf(node) {
  if (node.nodeType === 3) return node.nodeValue
  if (node.nodeType === 11) return [...node.childNodes].map(textOf).join('')
  if (node.nodeType !== 1) return ''
  const el = node
  if (el.tagName === 'MJX-CONTAINER') {
    const tex = el.getAttribute('data-tex')
    if (tex == null) return ''
    return el.getAttribute('data-display') === 'true' ? '\n$$\n' + tex + '\n$$\n' : '$' + tex + '$'
  }
  if (el.classList.contains('pts')) {
    const n = el.textContent.trim()
    return n ? ' [' + n + ']' : ''
  }
  if (el.classList.contains('msrc') || el.tagName === 'MJX-ASSISTIVE-MML' || el.tagName === 'svg') return ''
  if (el.tagName === 'IMG') {
    const src = el.getAttribute('src') || ''
    return src.startsWith('/fig/') ? '![](' + src + ')' : ''
  }
  const bits = [...el.childNodes].map(textOf).join('')
  if (el.tagName === 'P' || el.tagName === 'DIV' || el.tagName === 'TR' || el.tagName === 'BR') return bits.replace(/[ \t]+$/g, '') + '\n'
  return bits
}

function plain(range) {
  const r = range.cloneRange()
  const a = boxOf(r.startContainer)
  const b = boxOf(r.endContainer)
  if (a) r.setStartBefore(a)
  if (b) r.setEndAfter(b)
  return textOf(r.cloneContents()).replace(/[ \t]+\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim()
}

function paint() {
  for (const box of document.querySelectorAll('mjx-container.sel')) box.classList.remove('sel')
  const sel = document.getSelection()
  if (!sel || sel.isCollapsed || !sel.rangeCount) return
  const range = sel.getRangeAt(0)
  const node = range.commonAncestorContainer
  const host = (node.nodeType === 1 ? node : node.parentElement)?.closest?.('.q:not(.prev)')
  if (!host) return
  for (const box of host.querySelectorAll('mjx-container')) {
    if (range.intersectsNode(box)) box.classList.add('sel')
  }
}

if (typeof document !== 'undefined') {
  document.addEventListener('selectionchange', paint)
  document.addEventListener('copy', (e) => {
    const sel = document.getSelection()
    if (!sel || sel.isCollapsed || !sel.rangeCount) return
    const range = sel.getRangeAt(0)
    const node = range.commonAncestorContainer
    const el = node.nodeType === 1 ? node : node.parentElement
    if (!el?.closest('.q') || el.closest('.prev')) return
    const text = plain(range)
    if (!text || !e.clipboardData) return
    e.clipboardData.setData('text/plain', text)
    e.preventDefault()
  })
}

export function flush() {
  const queued = pending.splice(0)
  if (queued.length) typeset(queued)
}

window.flushMath = flush
