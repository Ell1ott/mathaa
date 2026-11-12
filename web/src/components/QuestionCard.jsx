import { AREAS } from '../areas.js'
import { LEVELS, label } from '../bank.js'
import { QuestionText } from './QuestionText.jsx'
import { Tags } from './Tag.jsx'

export function QuestionCard({ question, topics, areas = AREAS, saved, onOpen, onStar }) {
  return (
    <article
      className="card"
      tabIndex={0}
      role="button"
      onClick={onOpen}
      onKeyDown={(e) => { if (e.key === 'Enter') onOpen() }}
    >
      <div className="ch">
        <span className="qn">Q{question.n}</span>
        <span className="src">{question.l ? (LEVELS[question.l] || question.l) + ' · ' : ''}{label(question)}, Paper {question.p}{question.z ? ', ' + question.z : ''}</span>
        {question.m ? <span className="mk">{question.m} marks</span> : null}
      </div>
      <QuestionText className="prev q" text={question.t} limit={420} />
      <div className="foot">
        <Tags question={question} topics={topics} areas={areas} max={2} />
        <span
          className={'star' + (saved ? ' on' : '')}
          role="button"
          aria-label="Save question"
          onClick={(e) => { e.stopPropagation(); onStar() }}
        >
          {saved ? '★' : '☆'}
        </span>
      </div>
    </article>
  )
}
