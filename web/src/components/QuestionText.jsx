import { useEffect, useRef } from 'react'
import { fmt } from '../format.js'
import { typeset } from '../mathjax.js'

export function QuestionText({ text, limit, className }) {
  const ref = useRef(null)
  const html = fmt(text || '', limit)
  useEffect(() => {
    if (ref.current) typeset([ref.current])
  }, [html])
  return <div ref={ref} className={className} dangerouslySetInnerHTML={{ __html: html }} />
}
