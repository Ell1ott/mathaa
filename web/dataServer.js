import { execFile } from 'node:child_process'
import { createHash } from 'node:crypto'
import { createReadStream, existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from 'node:fs'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const CACHE = path.join(ROOT, 'web', '.cache')
const COVERS = path.join(ROOT, 'data', 'covers')
const CUT_NAME = /^[a-z0-9]+(?:-[a-z0-9]+)*\.png$/
const COVER_NAME = /^[a-z0-9]+(?:-[a-z0-9]+)*-[12]\.jpg$/
const ID_NAME = /^[a-z0-9]+(?:-[a-z0-9]+)*$/
const IMAGE_DIR = { cut: 'cuts', fig: 'figs', scheme: 'schemes' }

let ready
let files
let mupdf
let loading
let tail = Promise.resolve()
const docs = new Map()

export function imagePath(root, kind, name) {
  const folder = IMAGE_DIR[kind]
  if (!folder || !CUT_NAME.test(name)) return null
  return path.join(root, 'data', folder, name)
}

export function pdfPath(root, index, id) {
  if (!ID_NAME.test(id)) return null
  const rel = index[id]
  if (typeof rel !== 'string' || path.isAbsolute(rel) || rel.split(/[/\\]/).includes('..')) return null
  const abs = path.resolve(root, rel)
  const base = path.resolve(root)
  if (abs !== base && !abs.startsWith(base + path.sep)) return null
  return abs
}

export function dataServer() {
  return {
    name: 'mathaa-data',
    configureServer(server) {
      server.middlewares.use(handler)
    },
    configurePreviewServer(server) {
      server.middlewares.use(handler)
    },
  }
}

function handler(req, res, next) {
  handle(req, res, next).catch((err) => {
    if (res.headersSent) return
    sendText(res, 500, err.message || 'error')
  })
}

async function handle(req, res, next) {
  if (req.method !== 'GET') return next()
  let url
  try {
    url = new URL(req.url, 'http://127.0.0.1')
  } catch {
    return next()
  }
  let pathname
  try {
    pathname = decodeURIComponent(url.pathname)
  } catch {
    return sendText(res, 400, 'bad path')
  }
  const route = routeOf(pathname)
  if (!route) return next()
  ready ??= ensureBank()
  await ready
  files ??= JSON.parse(await readFile(path.join(CACHE, 'files.json'), 'utf8'))
  if (route.kind === 'bank') return sendStream(req, res, path.join(CACHE, 'questions.json'), 'application/json')
  if (route.kind === 'image') return sendImage(res, imagePath(ROOT, route.dir, route.name))
  if (route.kind === 'cover') return sendCover(res, route.name)
  if (route.kind === 'doc') return sendDoc(req, res, route.id)
  if (route.kind === 'page') return sendPage(res, url.searchParams)
  return next()
}

function routeOf(pathname) {
  if (pathname === '/questions.json') return { kind: 'bank' }
  const image = /^\/(cut|fig|scheme)\/([^/]+)$/.exec(pathname)
  if (image) return { kind: 'image', dir: image[1], name: image[2] }
  if (pathname.startsWith('/paper/')) return { kind: 'cover', name: pathname.slice('/paper/'.length) }
  if (pathname.startsWith('/doc/') && pathname.endsWith('.pdf')) {
    return { kind: 'doc', id: pathname.slice('/doc/'.length, -'.pdf'.length) }
  }
  if (pathname === '/pdf') return { kind: 'page' }
  return null
}

function ensureBank() {
  const python = existsSync(path.join(ROOT, '.venv', 'bin', 'python'))
    ? path.join(ROOT, '.venv', 'bin', 'python')
    : 'python3'
  return new Promise((resolve, reject) => {
    execFile(python, [path.join(ROOT, 'scripts', 'write_bank.py')], { cwd: ROOT }, (err, _stdout, stderr) => {
      if (err) reject(new Error(stderr || err.message))
      else resolve()
    })
  })
}

function sendImage(res, file) {
  if (!file || !existsSync(file)) return sendText(res, 404, 'image not on disk')
  return sendStream(null, res, file, 'image/png')
}

async function sendCover(res, name) {
  if (!COVER_NAME.test(name)) return sendText(res, 404, 'image not on disk')
  const paperId = name.replace(/-[12]\.jpg$/, '')
  const pdf = pdfPath(ROOT, files, paperId)
  if (!pdf || !existsSync(pdf)) return sendText(res, 404, 'image not on disk')
  await ensureCovers(paperId, pdf)
  const file = path.join(COVERS, name)
  if (!existsSync(file) || statSync(file).size === 0) return sendText(res, 404, 'image not on disk')
  return sendStream(null, res, file, 'image/jpeg', 'public, max-age=86400')
}

function sendDoc(req, res, id) {
  if (!id.startsWith('econ-') && !id.startsWith('phy-')) return sendText(res, 404, 'PDF not on disk')
  const pdf = pdfPath(ROOT, files, id)
  if (!pdf || !existsSync(pdf) || pdf.toLowerCase().includes('markscheme')) return sendText(res, 404, 'PDF not on disk')
  return sendStream(req, res, pdf, 'application/pdf')
}

async function sendPage(res, query) {
  const id = query.get('question')
  const page = query.get('page')
  if (!id || !page || !/^\d+$/.test(page)) return sendText(res, 400, 'bad page')
  const pdf = pdfPath(ROOT, files, id)
  if (!pdf || !existsSync(pdf)) return sendText(res, 404, 'PDF not on disk')
  const png = await pagePng(pdf, Number(page))
  if (!png) return sendText(res, 404, 'page not in PDF')
  return sendBytes(res, png, 'image/png', 'private, max-age=86400')
}

function pageCache(abs, page) {
  const stamp = statSync(abs).mtimeNs.toString()
  const name = createHash('sha1').update(`${abs}:${stamp}:${page}`).digest('hex').slice(0, 20) + '.png'
  return path.join(CACHE, 'pages', name)
}

async function pagePng(abs, page) {
  const dest = pageCache(abs, page)
  if (existsSync(dest)) return readFile(dest)
  await lib()
  return locked(() => {
    if (existsSync(dest)) return readFileSync(dest)
    const data = draw(abs, page, 100 / 72)
    if (!data) return null
    mkdirSync(path.dirname(dest), { recursive: true })
    writeFileSync(dest, data)
    return data
  })
}

async function ensureCovers(paperId, abs) {
  const targets = [1, 2].map((page) => path.join(COVERS, `${paperId}-${page}.jpg`))
  const pdfTime = statSync(abs).mtimeMs
  const fresh = targets.every((file) => existsSync(file) && statSync(file).mtimeMs >= pdfTime)
  if (fresh) return
  await lib()
  await locked(() => {
    const still = targets.every((file) => existsSync(file) && statSync(file).mtimeMs >= pdfTime)
    if (still) return
    mkdirSync(COVERS, { recursive: true })
    for (let i = 0; i < targets.length; i++) writeFileSync(targets[i], draw(abs, i + 1, null) ?? Buffer.alloc(0))
  })
}

function locked(fn) {
  const run = tail.then(fn, fn)
  tail = run.then(() => {}, () => {})
  return run
}

function lib() {
  loading ??= import('mupdf').then((mod) => {
    mupdf = mod.default
  })
  return loading
}

function draw(abs, pageNumber, scale) {
  // Called only from inside locked(), and it must not await: MuPDF is one wasm instance.
  const doc = openDoc(abs)
  if (pageNumber < 1 || pageNumber > doc.countPages()) return null
  const page = doc.loadPage(pageNumber - 1)
  try {
    const zoom = scale ?? 320 / pageWidth(page)
    const pixmap = page.toPixmap(mupdf.Matrix.scale(zoom, zoom), mupdf.ColorSpace.DeviceRGB, false, true)
    try {
      return Buffer.from(scale == null ? pixmap.asJPEG(50) : pixmap.asPNG())
    } finally {
      pixmap.destroy()
    }
  } finally {
    page.destroy()
  }
}

function pageWidth(page) {
  const bounds = page.getBounds()
  const width = Array.isArray(bounds) ? bounds[2] - bounds[0] : bounds.x1 - bounds.x0
  if (!width) throw new Error('page has no width')
  return width
}

function openDoc(abs) {
  const mtime = statSync(abs).mtimeNs.toString()
  const hit = docs.get(abs)
  if (hit && hit.mtime === mtime) return hit.doc
  if (hit) hit.doc.destroy()
  const doc = mupdf.Document.openDocument(readFileSync(abs), 'application/pdf')
  docs.set(abs, { mtime, doc })
  if (docs.size > 8) {
    const first = docs.keys().next().value
    docs.get(first).doc.destroy()
    docs.delete(first)
  }
  return doc
}

function sendStream(req, res, file, type, cache) {
  const stat = statSync(file)
  res.setHeader('Content-Type', type)
  res.setHeader('Accept-Ranges', 'bytes')
  if (cache) res.setHeader('Cache-Control', cache)
  const range = req && req.headers.range
  if (range) {
    const match = /^bytes=(\d*)-(\d*)$/.exec(range)
    if (!match || (match[1] === '' && match[2] === '')) {
      res.statusCode = 416
      res.setHeader('Content-Range', `bytes */${stat.size}`)
      res.end()
      return
    }
    let start
    let end
    if (match[1] === '') {
      const suffix = Number(match[2])
      start = Math.max(0, stat.size - suffix)
      end = stat.size - 1
    } else {
      start = Number(match[1])
      end = match[2] === '' ? stat.size - 1 : Number(match[2])
    }
    if (!Number.isFinite(start) || !Number.isFinite(end) || start > end || start >= stat.size) {
      res.statusCode = 416
      res.setHeader('Content-Range', `bytes */${stat.size}`)
      res.end()
      return
    }
    end = Math.min(end, stat.size - 1)
    res.statusCode = 206
    res.setHeader('Content-Range', `bytes ${start}-${end}/${stat.size}`)
    res.setHeader('Content-Length', String(end - start + 1))
    createReadStream(file, { start, end }).pipe(res)
    return
  }
  res.statusCode = 200
  res.setHeader('Content-Length', String(stat.size))
  createReadStream(file).pipe(res)
}

function sendBytes(res, body, type, cache) {
  res.statusCode = 200
  res.setHeader('Content-Type', type)
  res.setHeader('Content-Length', String(body.length))
  if (cache) res.setHeader('Cache-Control', cache)
  res.end(body)
}

function sendText(res, code, text) {
  const body = Buffer.from(text)
  res.statusCode = code
  res.setHeader('Content-Type', 'text/plain; charset=utf-8')
  res.setHeader('Content-Length', String(body.length))
  res.end(body)
}
