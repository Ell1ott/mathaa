import { useEffect, useRef, useState } from 'react'
import { AREAS } from '../areas.js'
import { calculator, paperName } from '../bank.js'
import { useSwipe } from '../useSwipe.js'
import { QuestionText } from './QuestionText.jsx'
import { Segment } from './Segment.jsx'
import { Tags } from './Tag.jsx'

function Icon({ children }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">{children}</svg>
  )
}

function Cut({ id, kind, active }) {
  const [missing, setMissing] = useState(false)
  const src = '/' + kind + '/' + encodeURIComponent(id) + '.png'
  useEffect(() => { setMissing(false) }, [src])
  const note = kind === 'scheme' ? 'No markscheme for this question.' : 'No printed cutout for this question.'
  return (
    <div className={kind === 'scheme' ? 'scheme paper' : 'paper'} hidden={!active}>
      {active && (missing
        ? <p className="note">{note}</p>
        : <img alt={kind === 'scheme' ? 'Markscheme for this question' : 'Question as printed on the paper'} src={src} onError={() => setMissing(true)} />)}
    </div>
  )
}

function PdfPages({ question, active }) {
  const first = question.a || 1
  const last = Math.min(question.b || first, first + 7)
  const pages = []
  for (let page = first; page <= last; page++) pages.push(page)
  return (
    <div className="paper" hidden={!active}>
      {active && pages.map((page) => (
        <img key={page} alt={'Question as printed, page ' + page} src={'/pdf?question=' + encodeURIComponent(question.i) + '&page=' + page} />
      ))}
    </div>
  )
}

function Body({ question, topics, areas, view, index, total, onOpenPaper }) {
  const calc = calculator(question)
  return (
    <>
      <div className="facts">
        <button type="button" className="srcbtn" onClick={() => onOpenPaper(question)}>{paperName(question)}</button>
        {question.m ? <span><b>{question.m}</b> marks</span> : null}
        {calc ? <span>{calc}</span> : null}
        <span>Pages {question.a}{question.b !== question.a ? '–' + question.b : ''}</span>
        <span>{index + 1} of {total} in current view</span>
      </div>
      <Tags question={question} topics={topics} areas={areas} max={9} style={{ marginBottom: 22 }} />
      {question.u === 'phys'
        ? <PdfPages question={question} active={view === 'paper'} />
        : <Cut id={question.i} kind="cut" active={view === 'paper'} />}
      {question.e
        ? <div className="scheme qwrap" hidden={view !== 'scheme'}><QuestionText className="q" text={question.e} /></div>
        : <Cut id={question.i} kind="scheme" active={view === 'scheme'} />}
      <div className="qwrap" hidden={view !== 'text'}>
        <QuestionText className="q" text={question.t} />
        {!question.v && question.c?.length > 0 && <div className="note">Topic tags for this question were assigned automatically and may not be exact.</div>}
      </div>
    </>
  )
}

export function QuestionSheet({ open, docs, index, view, question, questions, paper, papers, topics, areas = AREAS, saved, onClose, onIndex, onView, onStar, onCopy, onOpenPaper, copied }) {
  const sheetRef = useRef(null)
  const bodyRef = useRef(null)
  const reelRef = useRef(null)
  const optsRef = useRef({})
  const count = docs ? papers.length : questions.length
  optsRef.current = { enabled: open && !docs, index, count, onIndex }
  useSwipe(sheetRef, bodyRef, reelRef, optsRef, open && !docs, index)

  const atStart = index <= 0
  const atEnd = index >= count - 1
  const schemeOn = !!(question && question.k)

  return (
    <section
      ref={sheetRef}
      className={'sheet' + (open ? ' on' : '') + (docs ? ' docs' : '')}
      id="sheet"
      aria-hidden={!open}
      role="dialog"
      aria-label={docs ? 'Paper' : 'Question'}
    >
      <div ref={bodyRef} className={'sb' + (open && !docs ? ' deck' : '')} id="sbody">
        {open && docs && paper && (
          <iframe className="pframe" src={'/pdf?paper=' + encodeURIComponent(paper.i)} title={paperName(paper)} />
        )}
        {open && !docs && (
          <div className="reel" ref={reelRef}>
            {[-1, 0, 1].map((delta) => {
              const i = index + delta
              const q = questions[i]
              return (
                <div key={q ? q.i : 'gap-' + i} className="pane">
                  {q && <Body question={q} topics={topics} areas={areas} view={view} index={i} total={count} onOpenPaper={onOpenPaper} />}
                </div>
              )
            })}
          </div>
        )}
      </div>
      <div className="qfoot">
        <nav className="bar" aria-label="Question controls">
          <button type="button" id="close" aria-label="Close" onClick={onClose}><Icon><path d="M6 6l12 12M18 6L6 18" /></Icon></button>
          <span className="sep" />
          <button type="button" id="prev" aria-label="Previous question" disabled={atStart} onClick={() => onIndex(index - 1)}><Icon><path d="M15 5l-7 7 7 7" /></Icon></button>
          <span className="count" id="count">{docs && paper ? paperName(paper) : count ? (index + 1) + ' / ' + count : ''}</span>
          <button type="button" id="next" aria-label="Next question" disabled={atEnd} onClick={() => onIndex(index + 1)}><Icon><path d="M9 5l7 7-7 7" /></Icon></button>
          <span className="sep qonly" />
          <Segment
            className="seg qonly"
            label="Question view"
            options={[
              { value: 'text', label: 'Text', aria: 'Text', on: view === 'text', onClick: () => onView('text'), icon: <Icon><path d="M5 7h14M5 12h14M5 17h9" /></Icon> },
              { value: 'paper', label: 'Paper', aria: 'Paper', on: view === 'paper', onClick: () => onView('paper'), icon: <Icon><rect x="4" y="5" width="16" height="14" rx="2" /><circle cx="9" cy="10" r="1.4" /><path d="M20 16l-4.5-4-7.5 6" /></Icon> },
              { value: 'scheme', label: 'Scheme', aria: 'Markscheme', on: view === 'scheme', disabled: !schemeOn, onClick: () => onView('scheme'), icon: <Icon><rect x="5" y="3" width="14" height="18" rx="2" /><path d="M8 8h8M8 12h8M8 16h5" /></Icon> },
            ]}
          />
          <span className="sep qonly" />
          <button type="button" id="bm" className={'qonly' + (saved ? ' on' : '')} aria-label="Bookmark" aria-pressed={saved} onClick={onStar}>
            <Icon><path d="M6 4h12v17l-6-4-6 4z" /></Icon>
          </button>
          <button type="button" id="cp" className={'qonly' + (copied ? ' done' : '')} aria-label="Copy question text" onClick={onCopy}>
            <Icon><rect x="9" y="9" width="11" height="11" rx="2" /><path d="M5 15V5a2 2 0 0 1 2-2h10" /></Icon>
          </button>
        </nav>
      </div>
    </section>
  )
}

