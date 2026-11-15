import assert from 'node:assert/strict'
import test from 'node:test'
import { matchesQuestion } from './bank.js'

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

test('a selected area still allows its other topics when strict', () => {
  const S = filters({ a: new Set(['Calculus']), t: new Set(['5.1']), strict: true })
  assert.equal(matchesQuestion(calc, S, {}, null, ''), true)
  assert.equal(matchesQuestion(both, S, {}, null, ''), false)
})
