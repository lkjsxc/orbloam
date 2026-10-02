#!/usr/bin/env python3
"""Review/apply a bounded update to the committed graph, retaining live owner IDs.

This is a developer operation, never part of startup or normal CI. Specify only
reviewed function names. Unknown names and unresolved original identities fail.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

os.environ.setdefault('LKJSCRIPT', str(Path(__file__).resolve().parents[1] / 'runtime/lkjscript'))
from build import Author, ROOT, run
from stages import substitute, type_record
from game import compose


class Capture(Author):
    def __init__(self, docs):
        super().__init__(docs)
        self.definitions = {}
        self.test_definitions = {}
        self.port_definitions = {}

    def fn(self, name, *args, **kwargs):
        start = len(self.records)
        result = super().fn(name, *args, **kwargs)
        self.definitions[name] = self.records[start:]
        return result

    def test(self, name, *args, **kwargs):
        start = len(self.records)
        result = super().test(name, *args, **kwargs)
        self.test_definitions[name] = self.records[start:]
        return result

    def port(self, name, *args, **kwargs):
        start = len(self.records)
        result = super().port(name, *args, **kwargs)
        self.port_definitions[name] = self.records[start:]
        return result


def recorded_updates(folder, build, current_name, current_revision, chosen):
    """Reconstruct the actual accepted chain, including deferred intermediate builds."""
    baseline = build['authoring_stages'][-1]['accepted_revision']
    existing = {item['name']: item for item in build.get('updates', [])}
    by_revision = {}
    for receipt in folder.glob('*.apply.txt'):
        match = re.search(r'^revision base=(rev_[a-f0-9]+) result=(rev_[a-f0-9]+)', receipt.read_text(), re.MULTILINE)
        if not match:
            continue
        name = receipt.name.removesuffix('.apply.txt')
        item = {'name': name, 'base': match[1], 'revision': match[2]}
        for suffix, key in [('.lkjc', 'request_sha256'), ('.logical-plan', 'logical_plan_sha256'), ('.apply.txt', 'apply_receipt_sha256')]:
            item[key] = hashlib.sha256((folder / (name + suffix)).read_bytes()).hexdigest()
        functions = chosen if name == current_name else existing.get(name, {}).get('functions')
        if functions is not None:
            item['functions'] = functions
        if match[2] in by_revision:
            raise ValueError('Ambiguous accepted revision receipts: ' + match[2])
        by_revision[match[2]] = item
    result, seen, revision = [], set(), current_revision
    while revision != baseline:
        if revision in seen or revision not in by_revision:
            raise ValueError('Incomplete or cyclic accepted update history: ' + revision)
        seen.add(revision)
        item = by_revision[revision]
        result.append(item)
        revision = item['base']
    return list(reversed(result))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--functions', nargs='*', default=[])
    parser.add_argument('--tests', nargs='*', default=[])
    parser.add_argument('--delete-tests', nargs='*', default=[])
    parser.add_argument('--new-ports', nargs='*', default=[])
    parser.add_argument('--defer-build', action='store_true', help='Apply a reviewed intermediate revision without changing the shipped artifact')
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9A-Za-z-]+', args.name):
        parser.error('Use an alphanumeric update name')
    project = ROOT / 'project'
    folder = ROOT / 'authoring'
    work = ROOT / '.build' / args.name
    work.mkdir(parents=True, exist_ok=False)
    docs = ROOT / '.build/reference'
    if not docs.exists():
        run('capabilities', '--generate-docs', str(docs))
    author = Capture((docs / 'builtin-standard.md').read_text())
    author.bootstrap()
    compose(author)
    identities = {}
    for receipt in sorted(folder.glob('*.apply.txt')):
        text = receipt.read_text()
        package = re.search(r'^project .* package=(pkg_[a-f0-9]+)', text, re.MULTILINE).group(1)
        for symbol, owner in re.findall(r'^identity symbol=(\$\S+) id=(\S+)', text, re.MULTILINE):
            identities[symbol] = package + '/' + owner if owner.startswith('req_') else owner
    records = list(dict.fromkeys(r for r in author.records if type_record(r)))
    chosen = list(dict.fromkeys(args.functions))
    for name in chosen:
        definition = author.definitions[name]
        old = identities.get('$' + name)
        body_symbol = '$' + name + '-body'
        if old:
            block = next(r for r in definition if r.startswith('expression.block '))
            # Only the root is new. Existing parameters retain their exact owners.
            fresh = f'$update-{args.name}-{name}-body'
            block = re.sub(r'^expression.block as=\$[^\s]+', f'expression.block as={fresh}', block, count=1)
            records += [block, f'replace.body function={old} body={fresh}']
        else:
            records.extend(definition)
    for name in args.delete_tests:
        old = identities.get('$test-' + name)
        if old is None:
            raise ValueError(f'No accepted test to retire: {name}')
        records.append(f'delete.owner owner={old} policy=owned-closure')
    for name in args.tests:
        definition = author.test_definitions[name]
        for record in definition:
            # Updated tests get fresh test/root identities, even if a name is reused.
            records.append(re.sub(r'\$test-' + re.escape(name) + r'(?=[-\s]|$)',
                                  '$update-test-' + args.name + '-' + name, record))
    for name in args.new_ports:
        records.extend(author.port_definitions[name])
    # Existing roots should never be reused as new expression allocations.
    body = substitute('\n'.join(records), identities)
    body = re.sub(r'\(local ((?:param|bind)_[a-f0-9]+)\)', r'(local (exact \1))', body)
    status = run('status', project=project)
    base = re.search(r'^revision id=(rev_[a-f0-9]+)', status, re.MULTILINE).group(1)
    request = folder / (args.name + '.lkjc')
    if request.exists():
        raise FileExistsError(request)
    request.write_text(f'request base={base}\n{body}\n')
    plan = run('change', 'plan', '--input-file', request, '--output', folder / (args.name + '.logical-plan'), project=project)
    (folder / (args.name + '.plan.txt')).write_text(plan)
    token = re.search(r'\bplan_[a-f0-9]+\b', plan).group()
    applied = run('change', 'apply', '--input-file', request, '--plan', token, project=project)
    (folder / (args.name + '.apply.txt')).write_text(applied)
    revision = re.search(r'^revision base=rev_[a-f0-9]+ result=(rev_[a-f0-9]+)', applied, re.MULTILINE).group(1)
    if args.defer_build:
        print('ACCEPTED INTERMEDIATE REVISION', revision, '— shipped artifact intentionally unchanged')
        return
    artifact = work / 'application.lkja'
    built = run('build', '--output', artifact, project=project)
    (work / 'build.txt').write_text(built)
    # Install only completely built bytes, atomically; never write into a live data root.
    (ROOT / 'dist/application.lkja.next').write_bytes(artifact.read_bytes())
    (ROOT / 'dist/application.lkja.next').replace(ROOT / 'dist/application.lkja')
    build = json.loads((ROOT / 'dist/BUILD.json').read_text())
    build.update(artifact_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(), accepted_revision=revision)
    build['updates'] = recorded_updates(folder, build, args.name, revision, chosen)
    if 'web_assets' in build:
        build['web_assets'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in sorted((ROOT / 'web').iterdir()) if p.is_file()}
    (ROOT / 'dist/BUILD.json').write_text(json.dumps(build, indent=2) + '\n')
    names = ['application.lkja', 'service.deployment.json', 'BUILD.json']
    (ROOT / 'dist/SHA256SUMS').write_text(''.join(hashlib.sha256((ROOT/'dist'/n).read_bytes()).hexdigest() + '  ' + n + '\n' for n in names))
    print('UPDATED', revision)


if __name__ == '__main__':
    main()
