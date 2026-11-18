import assert from 'node:assert/strict'
import test from 'node:test'
import { filtersFrom } from './filters.js'
import { componentLabel, matchesPaper, matchesQuestion, paperLabel, papersOnly, prepare, topSubjects } from './bank.js'

function question(c, ar) {
  return { u: 'math', p: 1, y: 2024, s: 'May', m: 6, c, ar, i: 'q', h: '', v: 1 }
}

function filters(extra) {
  return {
    sub: 'math', p: new Set(), y: new Set(), s: new Set(), m: new Set(), l: new Set(),
    a: new Set(), t: new Set(), saved: false, ver: false, unc: false, strict: false,
    ...extra,
  }
}

const both = question(['5.1', '2.1'], ['Calculus', 'Functions'])
const calc = question(['5.1', '5.2'], ['Calculus'])

test('area filters keep questions that also cover other areas', () => {
  const S = filters({ a: new Set(['Calculus']) })
  assert.equal(matchesQuestion(both, S, {}, null, ''), true)
  assert.equal(matchesQuestion(calc, S, {}, null, ''), true)
})

test('strict area filters drop questions with an area outside the selection', () => {
  const S = filters({ a: new Set(['Calculus']), strict: true })
  assert.equal(matchesQuestion(both, S, {}, null, ''), false)
  assert.equal(matchesQuestion(calc, S, {}, null, ''), true)
  assert.equal(matchesQuestion(question(['2.1'], ['Functions']), S, {}, null, ''), false)
})

test('strict topic filters drop questions with an extra topic', () => {
  const loose = filters({ t: new Set(['5.1']) })
  const strict = filters({ t: new Set(['5.1']), strict: true })
  assert.equal(matchesQuestion(calc, loose, {}, null, ''), true)
  assert.equal(matchesQuestion(calc, strict, {}, null, ''), false)
  assert.equal(matchesQuestion(question(['5.1'], ['Calculus']), strict, {}, null, ''), true)
})

test('spanish papers stay out of math', () => {
  const bank = prepare({
    qs: [{ i: '2024-05-p1-q1', y: 2024, s: 'May', p: 1, z: '', n: 1, t: 'solve', c: ['1.1'], v: true, a: 1, b: 1, k: false }],
    ps: [
      { i: 'spanish-b-hl-2020-11-p1', y: 2020, s: 'November', p: 1, z: '', l: 'hl', u: 'spanish-b' },
      { i: 'spanish-b-hl-2020-11-p2-reading-comprehension-text-booklet', y: 2020, s: 'November', p: 2, l: 'hl', u: 'spanish-b', k: 'reading-comprehension-text-booklet' },
      { i: 'spanish-b-hl-2024-05-listening', y: 2024, s: 'May', p: 'Listening', l: 'hl', u: 'spanish-b', au: 1 },
    ],
    subs: [['spanish-b', 'Spanish B', 'Language acquisition']],
  })
  assert.equal(bank.papers.filter((paper) => (paper.u || 'math') === 'math').length, 1)
  assert.equal(bank.papers.filter((paper) => paper.u === 'spanish-b').length, 3)
  assert.equal(bank.papers.find((paper) => paper.p === 'Listening').au, 1)
  assert.equal(bank.papers.find((paper) => paper.k).au, undefined)
  assert.equal(bank.subs[0][1], 'Spanish B')
  assert.equal(papersOnly('spanish-b'), true)
  assert.equal(papersOnly('math'), false)
  assert.equal(papersOnly('phys'), false)
  const math = filters({ sub: 'math' })
  const spanish = bank.papers.find((paper) => paper.k)
  assert.equal(matchesPaper(spanish, math, null, ''), false)
  assert.equal(matchesPaper(spanish, filters({ sub: 'spanish-b' }), null, 'text booklet'), true)
  assert.equal(componentLabel(spanish.k), 'Reading comprehension text booklet')
  assert.equal(paperLabel('Listening'), 'Listening')
  assert.equal(filtersFrom('?sub=spanish-b&browse=questions').browse, 'papers')
})

test('a selected area still allows its other topics when strict', () => {
  const S = filters({ a: new Set(['Calculus']), t: new Set(['5.1']), strict: true })
  assert.equal(matchesQuestion(calc, S, {}, null, ''), true)
  assert.equal(matchesQuestion(both, S, {}, null, ''), false)
})

test('top subjects rank the busiest subjects first', () => {
  const groups = [
    ['Mathematics', [['math', 'IB Math AA HL']]],
    ['Sciences', [['phys', 'IB Physics'], ['chem', 'Chemistry']]],
  ]
  assert.deepEqual(topSubjects(groups, { phys: 10, math: 4, chem: 3 }).map(([id]) => id), ['phys', 'math', 'chem'])
  assert.equal(topSubjects(groups, {}, 2).length, 2)
})
