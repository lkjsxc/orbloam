"""Real native-process/HTTP test fixture. Never an alternative game implementation."""
from __future__ import annotations
import copy
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import shlex
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get('LKJSCRIPT', ROOT / 'runtime/lkjscript')).resolve()
ARTIFACT = Path(os.environ.get('ORBLOAM_ARTIFACT', ROOT / 'dist/application.lkja')).resolve()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def redact(text: str) -> str:
    # Command output can contain fixture credentials. Never put them in test failure reports.
    return re.sub(r'(?<![a-f0-9])[a-f0-9]{64}(?![a-f0-9])', '<redacted-64hex>', text)


def native(*args, timeout: float = 120):
    result = subprocess.run([str(BINARY), *map(str, args)], capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f'Native {args[0]} failed ({result.returncode}): {redact(result.stdout + result.stderr)[-4000:]}')
    return result.stdout


def execution_value(output: str):
    lines = [line for line in output.splitlines() if line.startswith('execution ')]
    if len(lines) != 1:
        raise AssertionError('Expected exactly one native execution record')
    fields = dict(word.split('=', 1) for word in shlex.split(lines[0])[1:])
    if json.loads(fields['cleanup'])['remaining_tasks'] != 0:
        raise AssertionError('Native command did not join its work')
    return json.loads(fields['value'])


def decode_snapshot(data):
    if isinstance(data, dict) and 'world' in data and 'me' in data:
        data = copy.deepcopy(data)
        data['world']['nodes'] = dict(data['world']['nodes'])
        for colony in data['world']['colonies']:
            for field in ['inventory', 'research', 'receipts']:
                colony[field] = dict(colony[field])
    return data


class NativeApp:
    def __init__(self, *, root: Path | None = None, initialize=True):
        if root is None:
            states = ROOT / '.test-state'
            states.mkdir(exist_ok=True)
            root = Path(tempfile.mkdtemp(prefix='native-', dir=states))
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        if not (self.root / 'application.lkja').exists():
            shutil.copy2(ARTIFACT, self.root / 'application.lkja')
        self.descriptor = json.loads((ROOT / 'dist/service.deployment.json').read_text())
        self.descriptor['artifact'] = 'application.lkja'
        self.descriptor['listen'] = '127.0.0.1:0'
        for grant in self.descriptor['grants']:
            if grant['adapter']['kind'] == 'data':
                grant['adapter']['root'] = 'data'
        self.deployment = self.root / 'service.deployment.json'
        self.deployment.write_text(json.dumps(self.descriptor, indent=2) + '\n')
        self.process = None
        self.log = None
        self.base = None
        self.port = None
        self.measurements = []
        if initialize:
            native('data', 'initialize', '--root', self.root / 'data')

    def command(self, target: str, arguments: list):
        descriptor = copy.deepcopy(self.descriptor)
        descriptor.update(target=target, listen=None, http=None, session=None, worker=None)
        # Explicit trusted local command; this does not alter the HTTP service's quotas.
        descriptor.pop('execution', None)
        descriptor.pop('runtime', None)
        path = self.root / ('command-' + target + '.deployment.json')
        path.write_text(json.dumps(descriptor, indent=2) + '\n')
        return native('run', '--deployment', path, '--arguments', json.dumps(arguments), timeout=180)

    def seed(self, population=512, age=0):
        output = self.command('fixture-create', [population, age])
        match = re.search(r'orbloam-fixture-token:([0-9a-f]{64})', output)
        if not match:
            raise AssertionError('Fixture did not create a world: ' + redact(output)[-2000:])
        return match.group(1)

    def start(self):
        if self.process is not None:
            raise RuntimeError('Server already started')
        log_path = self.root / 'server.log'
        self.log = log_path.open('w')
        self.process = subprocess.Popen([str(BINARY), 'serve', '--deployment', str(self.deployment)],
             cwd='/tmp', stdout=self.log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            text = log_path.read_text()
            for line in text.splitlines():
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if record.get('event') == 'ready':
                    address = record['local_address']
                    self.port = int(address.rsplit(':', 1)[1])
                    self.base = f'http://127.0.0.1:{self.port}/'
                    return self
            if self.process.poll() is not None:
                raise RuntimeError('Server exited before readiness: ' + redact(text)[-3000:])
            time.sleep(.03)
        self.stop()
        raise TimeoutError('Native server readiness timed out')

    def stop(self):
        if self.process is None:
            return
        process, self.process = self.process, None
        if process.poll() is None:
            process.send_signal(signal.SIGINT)
            try:
                process.wait(timeout=35)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                raise TimeoutError('Native server did not finish joined shutdown')
        if self.log:
            self.log.close()
            self.log = None
        if process.returncode != 0:
            text = (self.root / 'server.log').read_text()
            raise RuntimeError(f'Native server shutdown returned {process.returncode}: ' + redact(text)[-2500:])

    def request(self, path, method='GET', data=None, token=None, *, raw=None, headers=None, host='127.0.0.1'):
        connection = http.client.HTTPConnection(host, self.port, timeout=40)
        supplied = dict(headers or {})
        if token is not None:
            supplied['Authorization'] = 'Bearer ' + token
        if data is not None:
            raw = json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode()
            supplied.setdefault('Content-Type', 'application/json')
        started = time.monotonic()
        try:
            connection.request(method, '/' + path.lstrip('/'), body=raw, headers=supplied)
            response = connection.getresponse()
            body = response.read()
            response_headers = dict(response.getheaders())
            elapsed = time.monotonic() - started
            self.measurements.append({'path': '/' + path.lstrip('/'), 'method': method, 'status': response.status,
                                       'elapsed_seconds': elapsed, 'bytes': len(body)})
            if 'application/json' in response.getheader('Content-Type', ''):
                value = decode_snapshot(json.loads(body))
            else:
                value = body
            return response.status, value, response_headers
        finally:
            connection.close()

    def expect(self, expected, *args, **kwargs):
        status, value, _ = self.request(*args, **kwargs)
        if status != expected:
            raise AssertionError(f'{args[0]}: expected HTTP {expected}, got {status}: ' + redact(str(value))[:1500])
        return value

    def join(self, name='Acceptance colony', token=None):
        token = token or secrets.token_hex(32)
        result = self.expect(201, 'api/join', 'POST', {'name': name, 'token': token})
        assert result['token'] == token
        return token, result['id']

    def view(self, token):
        return self.expect(200, 'api/view', token=token)

    def sync(self, token, attempts=100):
        for _ in range(attempts):
            state = self.expect(200, 'api/sync', 'POST', {}, token)
            if state['backlog_ticks'] == 0:
                return state
        raise AssertionError('Bounded catch-up attempts exhausted')

    def action(self, token, op, **fields):
        state = self.sync(token)
        colony = next(c for c in state['world']['colonies'] if c['id'] == state['me'])
        action = dict(op=op, sequence=colony['sequence'] + 1, index=0, value=0, x=0, y=0, text='')
        action.update(fields)
        for _ in range(10):
            status, value, _ = self.request('api/action', 'POST', action, token)
            if status == 409 and value.get('error') == 'catchup_required':
                state = self.sync(token)
                continue
            if status != 200:
                raise AssertionError(f'Action {op}: HTTP {status}: {value}')
            self.before_action = state
            return value, action
        raise AssertionError('Action remained behind chronological frontier')

    def verify(self):
        if self.process is not None:
            raise RuntimeError('Stop the server before offline verification')
        return native('data', 'verify', '--root', self.root / 'data')

    def __enter__(self):
        return self.start()

    def __exit__(self, *_):
        self.stop()
