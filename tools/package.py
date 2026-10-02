#!/usr/bin/env python3
"""Package a committed, verified game and its exact runtime without saves or caches.

The default deliverable is a ready-to-run offline ZIP plus a source ZIP. Optional
Git history is a separate bundle, not a recursive payload inside the playable ZIP.
This operation never publishes to a remote repository or changes live data.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_SHA256 = '98a39bd192c1e98187a1a954f916f5ffc89ef2586317c25e1efa06c61b888c32'
REPORTS = ('acceptance.json', 'standalone.json', 'performance.json', 'rebuild.json',
           'catalogue.json', 'quiet-world/native.json', 'quiet-world/presentation.json',
           'quiet-world/browser/report.json')
RUNTIME_FILES = ('lkjscript', 'LICENSE', 'THIRD-PARTY-LICENSES.html', 'RELEASE-MANIFEST.json')
# Preserve historical recovery material in Git, without nesting it in a new
# playable package. These exact legacy files are not current build inputs.
HISTORICAL_RECOVERY_FILES = frozenset(('orbloam-reconstructed.bundle', 'RECOVER-SOURCE.txt'))


def git(*args: str) -> str:
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--with-history', action='store_true', help='Also create a separate local Git bundle')
    args = parser.parse_args()
    out = args.output.resolve()
    if out == ROOT or ROOT in out.parents:
        parser.error('Output must be outside the source checkout')
    if git('status', '--porcelain'):
        raise SystemExit('Commit accepted source and evidence first; dirty checkout refused.')
    artifact = digest(ROOT / 'dist/application.lkja')
    build = json.loads((ROOT / 'dist/BUILD.json').read_text())
    if build['artifact_sha256'] != artifact:
        raise SystemExit('Build identity does not match the shipped artifact')
    subprocess.run(['sha256sum', '-c', 'SHA256SUMS'], cwd=ROOT / 'dist', check=True)
    reports = {}
    for name in REPORTS:
        report = json.loads((ROOT / 'evidence' / name).read_text())
        if report.get('status') != 'passed' or report.get('artifact_sha256') != artifact:
            raise SystemExit('Missing or mismatched final verification: ' + name)
        if report.get('runtime_sha256', RUNTIME_SHA256) != RUNTIME_SHA256:
            raise SystemExit('Wrong verification runtime: ' + name)
        reports[name] = digest(ROOT / 'evidence' / name)
    if digest(ROOT / 'runtime/lkjscript') != RUNTIME_SHA256:
        raise SystemExit('Runtime is not the pinned official executable')
    for name in RUNTIME_FILES:
        path = ROOT / 'runtime' / name
        if path.is_symlink() or not path.is_file():
            raise SystemExit('Missing or unsafe runtime payload: ' + name)
    browser = json.loads((ROOT / 'evidence/quiet-world/browser/report.json').read_text())
    for name, expected in browser['assets'].items():
        if digest(ROOT / 'web' / name) != expected:
            raise SystemExit('Web source differs from the verified served bytes: ' + name)
    commit = git('rev-parse', 'HEAD')
    names = ['orbloam-quiet-world.zip', 'orbloam-source.zip', 'SHA256SUMS', 'PACKAGING.json']
    if args.with_history:
        names.append('orbloam-quiet-world.bundle')
    out.mkdir(parents=True, exist_ok=True)
    if any((out / name).exists() for name in names):
        raise SystemExit('Output already exists; choose a new output directory')
    metadata = {
        'schema': 'orbloam-offline-package-v2', 'edition': build['edition'],
        'source_commit': commit, 'accepted_revision': build['accepted_revision'],
        'artifact_sha256': artifact, 'runtime_sha256': RUNTIME_SHA256,
        'verification_reports_sha256': reports,
        'browser_test_mode': browser['mode'], 'browser_nonclaims': browser.get('nonclaims', []),
        'remote_publication_performed': False, 'contains_player_data': False,
    }
    metadata_bytes = (json.dumps(metadata, indent=2) + '\n').encode()
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    payload: list[tuple[str, Path]] = []
    for name in filter(None, tracked):
        if name in HISTORICAL_RECOVERY_FILES:
            continue
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise SystemExit('Unexpected tracked payload: ' + name)
        if name.startswith(('.test-state/', '.build/', 'runtime/', 'dist/data/', 'project/derived/')) or name.endswith(('.bundle', '.lkjd', '.pyc')):
            raise SystemExit('Save, cache, or recursive archive is tracked: ' + name)
        payload.append((name, path))
    payload += [('runtime/' + name, ROOT / 'runtime' / name) for name in RUNTIME_FILES]
    checksum_lines = [digest(path) + '  ' + name for name, path in payload]
    checksum_lines.append(hashlib.sha256(metadata_bytes).hexdigest() + '  PACKAGE.json')
    destination = out / names[0]
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, path in payload:
            archive.write(path, 'orbloam/' + name)
        archive.writestr('orbloam/PACKAGE.json', metadata_bytes)
        archive.writestr('orbloam/PACKAGE-SHA256SUMS', '\n'.join(checksum_lines) + '\n')
    source = out / 'orbloam-source.zip'
    subprocess.run(['git', 'archive', '--format=zip', '--prefix=orbloam/', '-o', str(source), 'HEAD'], cwd=ROOT, check=True)
    files = [destination, source]
    if args.with_history:
        branch = git('symbolic-ref', '--short', 'HEAD')
        bundle = out / 'orbloam-quiet-world.bundle'
        subprocess.run(['git', 'bundle', 'create', str(bundle), branch], cwd=ROOT, check=True)
        subprocess.run(['git', 'bundle', 'verify', str(bundle)], cwd=ROOT, check=True)
        files.append(bundle)
    (out / 'SHA256SUMS').write_text(''.join(digest(path) + '  ' + path.name + '\n' for path in files))
    metadata['files'] = {path.name: {'bytes': path.stat().st_size, 'sha256': digest(path)} for path in files}
    (out / 'PACKAGING.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(json.dumps(metadata, indent=2))


if __name__ == '__main__':
    main()
