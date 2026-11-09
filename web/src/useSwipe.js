import { useEffect, useLayoutEffect } from 'react'

// The reel stays mounted. Replacing the node under the finger makes iOS cancel the touch.
export function useSwipe(sheetRef, bodyRef, reelRef, optsRef, enabled, index) {
  useLayoutEffect(() => {
    if (!enabled) return
    const body = bodyRef.current
    const reel = reelRef.current
    if (!body || !reel) return
    const w = body.clientWidth
    for (const pane of reel.children) pane.style.width = w + 'px'
    reel.style.transition = 'none'
    reel.style.transform = 'translate3d(' + -w + 'px,0,0)'
  }, [enabled, index, bodyRef, reelRef])

  useEffect(() => {
    const sheet = sheetRef.current
    const body = bodyRef.current
    if (!sheet || !body || !enabled) return undefined
    let on = false
    let busy = false
    let x0 = 0
    let y0 = 0
    let x = 0
    let t0 = 0
    let vx = 0
    let mode = 0
    let width = 0

    const point = (e) => (e.changedTouches ? e.changedTouches[0] : e.touches ? e.touches[0] : e)
    const strip = () => reelRef.current
    const place = (px, animate) => {
      const reel = strip()
      if (!reel) return
      reel.style.transition = animate ? 'transform .34s cubic-bezier(.32,.72,0,1)' : 'none'
      reel.style.transform = 'translate3d(' + px + 'px,0,0)'
    }
    const fit = () => {
      const reel = strip()
      if (!reel) return 0
      const w = body.clientWidth
      for (const pane of reel.children) pane.style.width = w + 'px'
      return w
    }

    function slide(dest) {
      const { index: cur, onIndex } = optsRef.current
      const reel = strip()
      if (!reel) {
        busy = false
        if (dest !== cur) onIndex(dest)
        return
      }
      busy = true
      on = false
      mode = 0
      const target = dest > cur ? -2 * width : dest < cur ? 0 : -width
      place(target, true)
      let done = false
      const finish = () => {
        if (done) return
        done = true
        busy = false
        if (dest !== cur) onIndex(dest)
      }
      reel.addEventListener('transitionend', finish, { once: true })
      setTimeout(finish, 380)
    }

    function down(e) {
      if (!optsRef.current.enabled || busy || !sheet.classList.contains('on')) return
      if (!e.touches || e.touches.length !== 1) return
      if (e.target.closest('.qfoot,button,a,input,select,textarea')) return
      const p = point(e)
      on = true
      mode = 0
      x0 = x = p.clientX
      y0 = p.clientY
      t0 = e.timeStamp
      vx = 0
      width = body.clientWidth
    }

    function move(e) {
      if (!on) return
      const p = point(e)
      const dx = p.clientX - x0
      const dy = p.clientY - y0
      if (!mode) {
        if (Math.abs(dx) < 12 && Math.abs(dy) < 12) return
        mode = Math.abs(dx) > Math.abs(dy) ? 1 : 2
        if (mode === 2) { on = false; return }
        width = fit() || width
      }
      if (mode !== 1 || !strip()) return
      if (e.cancelable) e.preventDefault()
      const dt = Math.max(1, e.timeStamp - t0)
      vx = (p.clientX - x) / dt
      x = p.clientX
      t0 = e.timeStamp
      const { index: cur, count } = optsRef.current
      let shift = -width + dx
      const min = cur >= count - 1 ? -width : -2 * width
      const max = cur <= 0 ? -width : 0
      if (shift > max) shift = max + (shift - max) * 0.28
      if (shift < min) shift = min + (shift - min) * 0.28
      place(shift, false)
    }

    function up(e) {
      if (!on) return
      const dx = point(e).clientX - x0
      on = false
      if (mode !== 1 || !strip()) { mode = 0; return }
      const { index: cur, count } = optsRef.current
      let dest = cur
      if (Math.abs(dx) > 56 || Math.abs(vx) > 0.45) {
        if (dx < 0 && cur < count - 1) dest = cur + 1
        else if (dx > 0 && cur > 0) dest = cur - 1
      }
      mode = 0
      slide(dest)
    }

    function cancel() {
      if (busy) return
      on = false
      mode = 0
      if (strip()) slide(optsRef.current.index)
    }

    const ro = new ResizeObserver(() => {
      if (on || busy) return
      const w = fit()
      if (w) place(-w, false)
    })
    ro.observe(body)
    sheet.addEventListener('touchstart', down, { passive: true })
    sheet.addEventListener('touchmove', move, { passive: false })
    sheet.addEventListener('touchend', up)
    sheet.addEventListener('touchcancel', cancel)
    return () => {
      ro.disconnect()
      sheet.removeEventListener('touchstart', down)
      sheet.removeEventListener('touchmove', move)
      sheet.removeEventListener('touchend', up)
      sheet.removeEventListener('touchcancel', cancel)
    }
  }, [enabled, sheetRef, bodyRef, reelRef, optsRef])
}
