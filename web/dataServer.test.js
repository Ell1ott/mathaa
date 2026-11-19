import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import { imagePath, pdfPath } from './dataServer.js'

const root = '/repo'

test('image paths stay in the data folders', () => {
  assert.equal(
    imagePath(root, 'cut', 'specimen-2021-p1-q1.png'),
    path.join(root, 'data', 'cuts', 'specimen-2021-p1-q1.png'),
  )
  assert.equal(imagePath(root, 'fig', '../secrets.png'), null)
  assert.equal(imagePath(root, 'scheme', 'Bad.PNG'), null)
  assert.equal(
    imagePath(root, 'scheme', 'phy-hl-2009-05-p2-tz1-qA1.png'),
    path.join(root, 'data', 'schemes', 'phy-hl-2009-05-p2-tz1-qA1.png'),
  )
  assert.equal(imagePath(root, 'cut', 'a/b.png'), null)
})

test('pdf paths stay inside the repo', () => {
  const files = { 'phy-hl-2000-05-p1-q1': 'papers/library/sciences/physics/hl/2000-05/en/p1.pdf' }
  assert.equal(
    pdfPath(root, files, 'phy-hl-2000-05-p1-q1'),
    path.resolve(root, files['phy-hl-2000-05-p1-q1']),
  )
  assert.equal(pdfPath(root, { x: '../etc/passwd' }, 'x'), null)
  assert.equal(pdfPath(root, files, '../x'), null)
  assert.equal(pdfPath(root, { abs: '/etc/passwd' }, 'abs'), null)
})
