import { useEffect, useLayoutEffect, useState } from 'react'

export function useSwipe(sheetRef, bodyRef, optsRef, enabled) {
  const [swipe, setSwipe] = useState(null)

  useEffect(() => {
    if (!enabled) setSwipe(null)
  }, [enabled])

  useEffect(() => {
    const sheet = sheetRef.current
    const body = bodyRef.current
    if (!sheet || !body) return undefined
    let on = false
    let busy = false
    let x0 = 0
    let y0 = 0
    let x = 0
    let t0 = 0
    let vx = 0
    let mode = 0
    let base = 0
    let width = 0

    const point = (e) => (e.changedTouches ? e.changedTouches[0] : e.touches ? e.touches[0] : e)
    const strip = () => body.querySelector('.reel')
    const place = (px) => {
      const reel = strip()
      if (reel) reel.style.transform = 'translate3d(' + px + 'px,0,0)'
    }

    function slide(dest) {
      const reel = strip()
      const { index, onIndex } = optsRef.current
      if (!reel) {
        busy = false
        setSwipe(null)
        if (dest !== index) onIndex(dest)
        return
      }
      busy = true
      on = false
      mode = 0
      const target = dest > index ? -2 * width : dest < index ? 0 : -width
      reel.style.transition = 'transform .34s cubic-bezier(.32,.72,0,1)'
      place(target)
      let done = false
      const finish = () => {
        if (done) return
        done = true
        busy = false
        reel.style.transition = 'none'
        setSwipe(null)
        if (dest !== index) onIndex(dest)
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
        width = body.clientWidth
        base = -width
        setSwipe({ width, pad: getComputedStyle(body).padding, top: body.scrollTop, dx })
        return
      }
      if (mode !== 1) return
      if (e.cancelable) e.preventDefault()
      const dt = Math.max(1, e.timeStamp - t0)
      vx = (p.clientX - x) / dt
      x = p.clientX
      t0 = e.timeStamp
      const { index, count } = optsRef.current
      let shift = base + (p.clientX - x0)
      const min = index >= count - 1 ? -width : -2 * width
      const max = index <= 0 ? -width : 0
      if (shift > max) shift = max + (shift - max) * 0.28
      if (shift < min) shift = min + (shift - min) * 0.28
      const reel = strip()
      if (!reel) return
      reel.style.transition = 'none'
      place(shift)
    }

    function up(e) {
      if (!on) return
      const dx = point(e).clientX - x0
      on = false
      if (mode !== 1) { mode = 0; return }
      const { index, count, onIndex } = optsRef.current
      let dest = index
      if (Math.abs(dx) > 56 || Math.abs(vx) > 0.45) {
        if (dx < 0 && index < count - 1) dest = index + 1
        else if (dx > 0 && index > 0) dest = index - 1
      }
      mode = 0
      if (!strip()) {
        setSwipe(null)
        if (dest !== index) onIndex(dest)
        return
      }
      slide(dest)
    }

    function cancel() {
      if (busy) return
      on = false
      mode = 0
      if (strip()) slide(optsRef.current.index)
    }

    sheet.addEventListener('touchstart', down, { passive: true })
    sheet.addEventListener('touchmove', move, { passive: false })
    sheet.addEventListener('touchend', up)
    sheet.addEventListener('touchcancel', cancel)
    return () => {
      sheet.removeEventListener('touchstart', down)
      sheet.removeEventListener('touchmove', move)
      sheet.removeEventListener('touchend', up)
      sheet.removeEventListener('touchcancel', cancel)
    }
  }, [sheetRef, bodyRef, optsRef])

  useLayoutEffect(() => {
    if (!swipe) return
    const reel = bodyRef.current?.querySelector('.reel')
    if (!reel) return
    reel.style.transition = 'none'
    reel.style.transform = 'translate3d(' + (-swipe.width + swipe.dx) + 'px,0,0)'
  }, [swipe, bodyRef])

  return swipe
}
