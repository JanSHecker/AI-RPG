import { spawn, spawnSync } from 'node:child_process'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'

const task = process.argv[2]
const repoRoot = fileURLToPath(new URL('../', import.meta.url))
const backendDir = path.join(repoRoot, 'backend')
const backendSrcDir = path.join(backendDir, 'src')

const pythonCandidates =
  process.platform === 'win32'
    ? [
        { command: 'py', args: ['-3'] },
        { command: 'python', args: [] },
        { command: 'python3', args: [] },
      ]
    : [
        { command: 'python3', args: [] },
        { command: 'python', args: [] },
      ]

function resolvePython() {
  for (const candidate of pythonCandidates) {
    const probe = spawnSync(candidate.command, [...candidate.args, '--version'], {
      stdio: 'ignore',
    })
    if (probe.status === 0) {
      return candidate
    }
  }

  throw new Error('No supported Python interpreter was found. Tried python3, python, and py -3.')
}

function runWithPython(args, extraEnv = {}) {
  const python = resolvePython()
  const pythonPath = process.env.PYTHONPATH
    ? `${backendSrcDir}${path.delimiter}${process.env.PYTHONPATH}`
    : backendSrcDir
  const child = spawn(python.command, [...python.args, ...args], {
    cwd: backendDir,
    env: { ...process.env, PYTHONPATH: pythonPath, ...extraEnv },
    stdio: 'inherit',
  })

  child.on('exit', (code, signal) => {
    if (signal) {
      process.kill(process.pid, signal)
      return
    }
    process.exit(code ?? 0)
  })
}

switch (task) {
  case 'install':
    runWithPython(['-m', 'pip', 'install', '-e', '.[dev]'])
    break
  case 'dev':
    runWithPython(['-m', 'ai_rpg.web.main'])
    break
  default:
    console.error('Usage: node ./scripts/backend.mjs <install|dev>')
    process.exit(1)
}
