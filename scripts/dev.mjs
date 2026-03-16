import { spawn } from 'node:child_process'
import process from 'node:process'

const isWindows = process.platform === 'win32'
const nodeCommand = process.execPath

const children = []
let shuttingDown = false

function quoteWindowsArg(value) {
  if (!/[\s"]/u.test(value)) {
    return value
  }

  return `"${value.replace(/"/g, '""')}"`
}

function stopChildren(signal = 'SIGTERM') {
  for (const child of children) {
    if (!child.killed) {
      child.kill(signal)
    }
  }
}

function spawnChild(name, command, args) {
  const child = isWindows
    ? spawn(
        'cmd.exe',
        ['/d', '/s', '/c', `${quoteWindowsArg(command)} ${args.map(quoteWindowsArg).join(' ')}`],
        {
          cwd: process.cwd(),
          env: process.env,
          stdio: 'inherit',
        },
      )
    : spawn(command, args, {
        cwd: process.cwd(),
        env: process.env,
        stdio: 'inherit',
      })

  child.on('exit', (code, signal) => {
    if (shuttingDown) {
      return
    }

    shuttingDown = true
    stopChildren(signal ?? 'SIGTERM')
    process.exit(code ?? 0)
  })

  child.on('error', (error) => {
    if (shuttingDown) {
      return
    }

    shuttingDown = true
    console.error(`[${name}] ${error.message}`)
    stopChildren('SIGTERM')
    process.exit(1)
  })

  children.push(child)
  return child
}

spawnChild('backend', nodeCommand, ['./scripts/backend.mjs', 'dev'])
spawnChild('frontend', nodeCommand, ['./scripts/frontend.mjs', 'dev'])

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => {
    if (shuttingDown) {
      return
    }

    shuttingDown = true
    stopChildren(signal)
    process.exit(0)
  })
}
