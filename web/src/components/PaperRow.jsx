export function PaperRow({ paper, onOpen }) {
  return (
    <button type="button" className="prow" onClick={onOpen}>
      <span className="qn">Paper {paper.p}{paper.z ? ' ' + paper.z : ''}</span>
      <span className="src">{paper.s + ' ' + paper.y}</span>
      <span className="mk">{paper.n} questions</span>
    </button>
  )
}
