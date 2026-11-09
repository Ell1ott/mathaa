const pending = []

export function typeset(els) {
  const list = els.filter(Boolean)
  if (!list.length) return
  if (!window.mjReady) {
    pending.push(...list)
    return
  }
  window.mjq = (window.mjq || Promise.resolve()).then(() => window.MathJax.typesetPromise(list)).catch(() => {})
}

export function flush() {
  const queued = pending.splice(0)
  if (queued.length) typeset(queued)
}

window.flushMath = flush
