import { useState } from 'react'
import { LEVELS } from '../bank.js'

const FOLDER = 'M28 0H98C112 0 118 4 126 12C134 20 140 24 154 24H192A28 28 0 0 1 220 52V172A28 28 0 0 1 192 200H28A28 28 0 0 1 0 172V28A28 28 0 0 1 28 0Z'
const FOLDER_BOX = 'M.127273 0H.445455C.509091 0 .536364 .02 .572727 .06C.609091 .1 .636364 .12 .7 .12H.872727A.127273 .14 0 0 1 1 .26V.86A.127273 .14 0 0 1 .872727 1H.127273A.127273 .14 0 0 1 0 .86V.14A.127273 .14 0 0 1 .127273 0Z'
const BOX = '-1.5 -1.5 223 203'

function Sheets({ src, hideSecond, onHideSecond }) {
  return (
    <>
      <svg className="back" viewBox={BOX} aria-hidden="true"><path d={FOLDER} /></svg>
      {!hideSecond && (
        <span className="fpage p2"><img alt="" src={src + '2.jpg'} loading="lazy" onError={onHideSecond} /></span>
      )}
      <span className="fpage p1"><img alt="" src={src + '1.jpg'} loading="lazy" /></span>
    </>
  )
}

export function PaperRow({ paper, onOpen }) {
  const [hideSecond, setHideSecond] = useState(false)
  const level = paper.l ? (LEVELS[paper.l] || paper.l) : ''
  const src = '/paper/' + encodeURIComponent(paper.i) + '-'
  const hide = () => setHideSecond(true)
  const clip = 'url(#f-' + paper.i.replace(/[^a-z0-9-]/gi, '') + ')'
  return (
    <button type="button" className="folder" onClick={onOpen}>
      <svg className="defs" width="0" height="0" aria-hidden="true">
        <clipPath id={clip.slice(5, -1)} clipPathUnits="objectBoundingBox"><path d={FOLDER_BOX} /></clipPath>
      </svg>
      <span className="fin">
        <span className="scene"><Sheets src={src} hideSecond={hideSecond} onHideSecond={hide} /></span>
        <span className="lower" style={{ clipPath: clip }} aria-hidden="true">
          <span className="scene"><Sheets src={src} hideSecond={hideSecond} onHideSecond={hide} /></span>
        </span>
        <span className="front" style={{ clipPath: clip }}>
          <span className="ft">Paper {paper.p}{paper.z ? ' ' + paper.z : ''}</span>
          <span className="fm">{[level, paper.s + ' ' + paper.y].filter(Boolean).join(' · ')}</span>
          {paper.n ? <span className="fs">{paper.n} questions</span> : null}
        </span>
        <svg className="rim" viewBox={BOX} aria-hidden="true"><path d={FOLDER} /></svg>
      </span>
    </button>
  )
}
