import { spawn } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'

const task = process.argv[2]
const isWindows = process.platform === 'win32'
const repoRoot = fileURLToPath(new URL('../', import.meta.url))
const frontendDir = path.join(repoRoot, 'frontend')
const installCommand = fs.existsSync(path.join(frontendDir, 'package-lock.json')) ? 'ci' : 'install'

const taskArgs = {
  install: ['--prefix', 'frontend', installCommand],
  dev: ['--prefix', 'frontend', 'run', 'dev', '--', '--host', '127.0.0.1'],
  build: ['--prefix', 'frontend', 'run', 'build'],
  test: ['--prefix', 'frontend', 'run', 'test'],
  lint: ['--prefix', 'frontend', 'run', 'lint'],
}

function quoteWindowsArg(value) {
  if (!/[\s"]/u.test(value)) {
    return value
  }

  return `"${value.replace(/"/g, '""')}"`
}

function spawnNpm(args) {
  return isWindows
    ? spawn('cmd.exe', ['/d', '/s', '/c', `npm.cmd ${args.map(quoteWindowsArg).join(' ')}`], {
        cwd: process.cwd(),
        env: process.env,
        stdio: 'inherit',
      })
    : spawn('npm', args, {
        cwd: process.cwd(),
        env: process.env,
        stdio: 'inherit',
      })
}

if (!(task in taskArgs)) {
  console.error('Usage: node ./scripts/frontend.mjs <install|dev|build|test|lint>')
  process.exit(1)
}

const child = spawnNpm(taskArgs[task])

child.on('exit', (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal)
    return
  }

  process.exit(code ?? 0)
})
