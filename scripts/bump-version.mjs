import fs from 'node:fs';
import path from 'node:path';
import { execSync } from 'node:child_process';

const repoRoot = process.cwd();
const frontendDir = path.join(repoRoot, 'frontend');
const packageJsonPath = path.join(frontendDir, 'package.json');
const envFiles = [
  path.join(frontendDir, 'src', 'environments', 'environment.ts'),
  path.join(frontendDir, 'src', 'environments', 'environment.production.ts'),
];

const args = new Set(process.argv.slice(2));
const noCommit = args.has('--no-commit');

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function writeJson(filePath, data) {
  fs.writeFileSync(filePath, `${JSON.stringify(data, null, 2)}\n`, 'utf8');
}

function bumpPatch(version) {
  const m = /^(\d+)\.(\d+)\.(\d+)$/.exec(version || '');
  if (!m) {
    throw new Error(`Version invalida: ${version}. Debe ser semver x.y.z`);
  }

  const major = Number(m[1]);
  const minor = Number(m[2]);
  const patch = Number(m[3]) + 1;
  return `${major}.${minor}.${patch}`;
}

function updateAppVersionInEnv(filePath, version) {
  const source = fs.readFileSync(filePath, 'utf8');

  if (/appVersion\s*:\s*'[^']*'\s*,/.test(source)) {
    const updated = source.replace(/appVersion\s*:\s*'[^']*'\s*,/, `appVersion: '${version}',`);
    fs.writeFileSync(filePath, updated, 'utf8');
    return;
  }

  const updated = source.replace(/production\s*:\s*(true|false)\s*,/, (match) => `${match}\n  appVersion: '${version}',`);
  fs.writeFileSync(filePath, updated, 'utf8');
}

function run(command) {
  execSync(command, { stdio: 'inherit' });
}

function gitOutput(command) {
  return execSync(command, { encoding: 'utf8' }).trim();
}

function main() {
  const pkg = readJson(packageJsonPath);
  const nextVersion = bumpPatch(pkg.version);
  pkg.version = nextVersion;
  writeJson(packageJsonPath, pkg);

  for (const envFile of envFiles) {
    updateAppVersionInEnv(envFile, nextVersion);
  }

  if (noCommit) {
    console.log(`Version actualizada a v${nextVersion} (sin commit).`);
    return;
  }

  run('git add frontend/package.json frontend/src/environments/environment.ts frontend/src/environments/environment.production.ts');
  run(`git commit -m "chore(version): v${nextVersion}"`);
  console.log(`Version actualizada y comiteada: v${nextVersion}`);

  const branch = gitOutput('git rev-parse --abbrev-ref HEAD');
  console.log(`Branch actual: ${branch}`);
}

main();
