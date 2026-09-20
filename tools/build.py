#!/usr/bin/env python3
"""Build-time authoring only. The deployed HTTP server is lkjscript, not Python."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get('LKJSCRIPT', str(ROOT / 'runtime/lkjscript'))
STD = 'pkg_10000000000000000000000000000001'


def run(*args: str, project: Path | None = None) -> str:
    command = [BINARY] + (['--project', str(project)] if project else []) + list(map(str, args))
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600)
    print(result.stdout, end='', flush=True)
    if result.returncode:
        raise RuntimeError(f'Native command failed ({result.returncode}): {command}')
    return result.stdout


def lit(value):
    if isinstance(value, bool):
        return f'(bool {str(value).lower()})'
    if isinstance(value, int):
        return f'(i64 {value})'
    return '(text ' + json.dumps(value, ensure_ascii=False) + ')'


def loc(name):
    return f'(local {name})'


def field(value, name):
    return f'(field {value} (name {name}))'


def rec(**fields):
    return '(record structural ' + ' '.join(f'(field {k} {v})' for k, v in fields.items()) + ')'


def seq(*values):
    return '(sequence ' + ' '.join(values) + ')'


def choose(test, yes, no):
    return f'(if {test} {yes} {no})'


def let(bindings, result):
    return '(let ' + ' '.join(f'(binding {n} {v})' for n, v in bindings) + f' (in {result}))'


class Author:
    def __init__(self, docs: str):
        self.records = []
        self.owners = []
        for line in docs.splitlines():
            if line.startswith('owner '):
                self.owners.append(dict(word.split('=', 1) for word in line.split()[1:] if '=' in word))
        self.types = {}
        self.functions = {}
        self.effects = {}
        self.route_index = 0

    def ref(self, name, parent=None):
        if parent:
            parent = self.ref(parent).split('/')[-1]
        values = [o for o in self.owners if o.get('name') == name and o.get('parent') == (parent or 'package')]
        if len(values) != 1:
            raise ValueError(f'Ambiguous or missing builtin: {parent}:{name}: {values}')
        return values[0]['reference']

    def emit(self, line):
        self.records.append(line)

    def call(self, name, *args, types=()):
        target = name if name.startswith('$') else self.ref(name)
        generics = ' (types ' + ' '.join(types) + ')' if types else ''
        return f'(call {target}{generics}' + ((' ' + ' '.join(args)) if args else '') + ')'

    def cap(self, req, interface, operation, *args):
        return f'(capability-call ${req} {self.ref(operation, interface)}' + ((' ' + ' '.join(args)) if args else '') + ')'

    def variant(self, parent, case, payload=None):
        return f'(variant {self.ref(case, parent)}' + (f' {payload}' if payload else '') + ')'

    def nominal_field(self, value, parent, name):
        return f'(field {value} {self.ref(name, parent)})'

    def structure(self, name, fields):
        self.types[name] = dict(fields)
        self.emit(f'type.structural-record as=@{name}')
        for i, (key, ty) in enumerate(fields.items()):
            self.emit(f'type.field parent=@{name} index={i} name={key} type={ty}')
        return '@' + name

    def named(self, name):
        self.emit(f'type.named as=@{name} declaration={self.ref(name)}')
        return '@' + name

    def list_type(self, name, item):
        self.emit(f'type.list as=@{name} item={item}')
        return '@' + name

    def map_type(self, name, key, value):
        self.emit(f'type.map as=@{name} key={key} value={value}')
        return '@' + name

    def fn(self, name, parameters, result, body, effects=()):
        self.functions[name] = (parameters, result)
        self.effects[name] = effects
        args = [loc(f'${name}-{p}') for p in parameters]
        body = body(*args) if callable(body) else body
        for key, ty in parameters.items():
            self.emit(f'add.parameter as=${name}-{key} function=${name} name={key} type={ty}')
        self.emit(f'expression.block as=${name}-definition-root\n  {body}\nexpression.end')
        self.emit(f'create.function as=${name} module=$game name={name} visibility=private result={result} effect={"task" if effects else "pure"} body=${name}-definition-root')
        for i, requirement in enumerate(effects):
            self.emit(f'effect.requirement parent=${name} index={i} requirement=${requirement}')
        return '$' + name

    def requirement(self, name, interface, operations, calls=256):
        self.emit(f'add.requirement as=${name} component=$component name={name} interface={self.ref(interface)}')
        for i, op in enumerate(operations):
            self.emit(f'requirement.operation parent=${name} index={i} operation={self.ref(op, interface)}')
        self.emit(f'requirement.limit parent=${name} index=0 name=maximum_calls maximum={calls} unit=calls')

    def port(self, name, function, target=None, method=None, path=None):
        params, result = self.functions[function]
        effects = self.effects[function]
        if effects:
            self.emit(f'effect.row as=@{name}-effects')
            for i, req in enumerate(effects):
                self.emit(f'effect.requirement parent=@{name}-effects index={i} requirement=${req}')
            self.emit(f'type.task-function as=@{name}-port result={result} effect=@{name}-effects')
        else:
            self.emit(f'type.function as=@{name}-port result={result}')
        for i, ty in enumerate(params.values()):
            self.emit(f'type.argument parent=@{name}-port index={i} type={ty}')
        self.emit(f'add.port as=${name}-port component=$component name={name} type=@{name}-port function=${function}')
        if method:
            self.route_index += 1
            self.emit(f'add.http-route as=$route-{self.route_index} target=$world method={method} path={json.dumps(path)} port=${name}-port')
        elif target:
            self.emit(f'create.target as=${name}-target name={target} component=$component port=${name}-port runner=command')

    def test(self, name, actual, expected):
        for suffix, body in [('actual', actual), ('expected', expected)]:
            self.emit(f'expression.block as=$test-{name}-{suffix}\n  {body}\nexpression.end')
        self.emit(f'create.test as=$test-{name} module=$game name={name} visibility=private actual=$test-{name}-actual expected=$test-{name}-expected')

    def transaction(self, body, result='@Response'):
        outcome = self.ref('TransactionOutcome')
        reason = self.ref('TransactionAbortReason')
        committed = self.ref('Committed', 'TransactionOutcome')
        aborted = self.ref('Aborted', 'TransactionOutcome')
        condition = self.ref('ConditionFailed', 'TransactionAbortReason')
        conflict = self.ref('Conflict', 'TransactionAbortReason')
        return f'(match (transaction-outcome $data (types {result}) (outcome {outcome} {reason} {committed} {aborted} {condition} {conflict}) (binding tx) {body}) (arm {committed} (payload committed {result}) (local committed)) (arm {aborted} (payload reason @TransactionAbortReason) {self.error(409, "transaction_conflict")}))'

    def response(self, status, body, content_type='application/json; charset=utf-8'):
        return self.call('$respond', lit(status) if isinstance(status, int) else status, body, lit(content_type))

    def json_response(self, body, ty, status=200):
        return self.response(status, self.call('json-encode', body, types=(ty,)))

    def error(self, status, code):
        return self.response(status, self.call('bytes-from-text', lit(json.dumps({'error': code}))))

    def key(self, text):
        return '(list @DataKeyPart ' + self.variant('DataKeyPart', 'Text', text) + ')'

    def get(self, key):
        return self.cap('data', 'DataStore', 'get', '(static-text "orbloam")', self.key(key))

    def put(self, key, value, ty, expectation):
        return self.cap('data', 'DataStore', 'put', '(static-text "orbloam")', self.key(key), self.call('data-encode', value, types=(ty,)), expectation)

    def bootstrap(self):
        self.emit('create.module as=$game name=orbloam')
        self.emit('create.component as=$component module=$game name=orbloam visibility=public')
        self.structure('Header', {'name': 'text', 'value': 'bytes'})
        self.list_type('Headers', '@Header')
        self.emit('type.stream as=@Body item=bytes')
        self.list_type('Texts', 'text')
        self.map_type('Query', 'text', '@Texts')
        self.structure('Request', {'body': '@Body', 'headers': '@Headers', 'method': 'text', 'path': 'text', 'query': 'text', 'query_parameters': '@Query'})
        self.structure('Response', {'body': 'bytes', 'headers': '@Headers', 'status': 'i64'})
        for ty in ['DataKeyPart', 'DataEntry', 'DataSchema', 'DataExpectation', 'TransactionAbortReason']:
            self.named(ty)
        self.list_type('Entries', '@DataEntry')
        def respond(status, body, content_type):
            headers = [('content-type', content_type), ('cache-control', lit('no-store')),
                       ('x-content-type-options', lit('nosniff')), ('referrer-policy', lit('no-referrer')),
                       ('content-security-policy', lit("default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"))]
            return rec(status=status, body=body, headers='(list @Header ' + ' '.join(
                rec(name=lit(k), value=self.call('bytes-from-text', v)) for k, v in headers) + ')')
        self.fn('respond', {'status': 'i64', 'body': 'bytes', 'content-type': 'text'}, '@Response', respond)

        self.requirement('data', 'DataStore', ['schema-read', 'schema-set', 'get', 'put', 'transaction'])
        self.requirement('streams', 'ByteStream', ['close', 'read-all', 'read'])
        self.requirement('clock', 'WallClock', ['utc-milliseconds'], 8)
        self.requirement('random', 'SecureRandom', ['bytes'], 8)
        self.schema()
        self.fn('authoring-ready', {}, 'bool', lit(True))
        self.port('authoring-ready', 'authoring-ready', target='authoring-ready')

    def schema(self):
        identity = 'orbloam-world-v1'
        digest = hashlib.sha256(identity.encode()).hexdigest()
        schema = '(record ' + self.ref('DataSchema') + ' (field ' + self.ref('identity', 'DataSchema') + ' ' + lit(identity) + ') (field ' + self.ref('digest', 'DataSchema') + ' ' + self.call('bytes-from-text', lit(digest)) + '))'
        schemas = self.cap('data', 'DataStore', 'schema-read', '(static-text "orbloam")')
        first = self.call('list-get', loc('schemas'), lit(0), types=('@DataSchema',))
        valid = self.call('bool-and', self.call('text-equal', self.nominal_field(first, 'DataSchema', 'identity'), lit(identity)), self.call('bytes-equal', self.nominal_field(first, 'DataSchema', 'digest'), self.call('bytes-from-text', lit(digest))))
        missing = self.call('i64-equal', self.call('list-length', loc('schemas'), types=('@DataSchema',)), lit(0))
        initialize = self.cap('data', 'DataStore', 'schema-set', '(static-text "orbloam")', self.variant('DataSchemaExpectation', 'Missing'), schema)
        self.fn('schema-ready', {}, 'bool', let([('schemas', schemas)], choose(missing, initialize, valid)), ('data',))


def main():
    os.chdir(ROOT)
    if run('--version').strip() != 'lkjscript 0.1.38':
        raise RuntimeError('This source requires the pinned lkjscript 0.1.38 runtime')
    build_root = ROOT / '.build'
    build_root.mkdir(exist_ok=True)
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resume', type=Path, help='Resume only an unchanged accepted authoring prefix')
    options = parser.parse_args()
    work = options.resume.resolve() if options.resume else Path(tempfile.mkdtemp(prefix='author-', dir=build_root))
    project = work / 'project'
    docs = work / 'reference'
    if options.resume:
        revision = re.search(r'request base=(rev_[a-f0-9]+)', (work / '01-ecology.lkjc').read_text()).group(1)
    else:
        created = run('new', str(project), '--template', 'http', '--name', 'orbloam')
        (work / 'creation.txt').write_text(created)
        revision = re.search(r'revision id=(rev_[a-f0-9]+)', created).group(1)
        run('capabilities', '--generate-docs', str(docs))
    author = Author((docs / 'builtin-standard.md').read_text())
    author.bootstrap()
    from game import compose
    compose(author)
    from stages import publish
    revision, proofs = publish(author, revision, work, project, run)
    checked = run('check', project=project)
    (work / 'check.txt').write_text(checked)
    artifact = work / 'application.lkja'
    if artifact.exists():
        import time
        artifact.rename(work / ('predecessor-' + str(time.time_ns()) + '.lkja'))
    built = run('build', '--output', str(artifact), project=project)
    (work / 'build.txt').write_text(built)
    dist = ROOT / 'dist'
    dist.mkdir(exist_ok=True)
    shutil.copy2(artifact, dist / 'application.lkja')
    deployment = json.loads((project / 'service.deployment.json').read_text())
    deployment['artifact'] = 'application.lkja'
    deployment['target'] = 'world'
    deployment['listen'] = '127.0.0.1:8080'
    deployment['runtime']['maximum_concurrent_tasks'] = 1
    deployment['runtime']['maximum_queued_tasks'] = 64
    deployment['http']['maximum_request_body_bytes'] = 4096
    deployment['grants'] = []
    adapters = {'streams': {'kind': 'byte_stream'}, 'clock': {'kind': 'wall_clock'}, 'random': {'kind': 'secure_random'}, 'data': {'kind': 'data', 'root': 'data', 'namespace': 'orbloam', 'limits': {'maximum_space_name_bytes': 128, 'maximum_key_parts': 4, 'maximum_key_bytes': 512, 'maximum_value_bytes': 1048576, 'maximum_transaction_mutations': 64, 'maximum_transaction_bytes': 4194304, 'maximum_scan_items': 256, 'maximum_scan_bytes': 4194304, 'maximum_scan_work': 10000, 'maximum_live_transactions': 8}}}
    for name, adapter in adapters.items():
        deployment['grants'].append({'requirement': name, 'sharing_domain': 'orbloam-' + name, 'authority_revision': hashlib.sha256(('orbloam-v1:' + name).encode()).hexdigest(), 'adapter': adapter})
    (dist / 'service.deployment.json').write_text(json.dumps(deployment, indent=2) + '\n')
    (dist / 'BUILD.json').write_text(json.dumps({'runtime': 'v0.1.38', 'artifact_sha256': hashlib.sha256(artifact.read_bytes()).hexdigest(), 'accepted_revision': revision, 'authoring_stages': proofs}, indent=2) + '\n')
    (dist / 'SHA256SUMS').write_text(''.join(hashlib.sha256((dist / name).read_bytes()).hexdigest() + '  ' + name + '\n' for name in ['application.lkja', 'service.deployment.json']))
    (build_root / 'latest').write_text(str(work) + '\n')
    print('BUILT', dist / 'application.lkja', flush=True)


if __name__ == '__main__':
    main()
