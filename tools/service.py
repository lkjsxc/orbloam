"""Native HTTP, secret lookup, strict decoding, idempotence and durable transactions."""
from __future__ import annotations
import json
from pathlib import Path
from meaning import I, L, F, R, IF, LET, SEQ
from catalog import CATALOG, RAW


def compose(g):
    a, c = g.a, g.c
    a.emit('create.target as=$world name=world component=$component runner=http')
    a.structure('Error', {'error': 'text'})
    a.structure('Join', {'name': 'text', 'token': 'text'})
    a.structure('Joined', {'id': 'i64', 'token': 'text'})
    a.structure('WorldRead', {'exists': 'bool', 'valid': 'bool', 'world': '@World', 'expectation': '@DataExpectation'})
    a.structure('Media', {'count': 'i64', 'valid': 'bool'})
    g.fn('error-response', {'status': 'i64', 'code': 'text'}, '@Response', lambda status, code:
         a.response(status, c('json-encode', R(error=code), types=('@Error',))))
    error = lambda status, code: c('$error-response', I(status), I(code) if isinstance(code, str) and not code.startswith('(') else code)
    g.fn('media-step', {'state': '@Media', 'header': '@Header'}, '@Media', lambda state, header:
         IF(g.text_eq(F(header, 'name'), I('content-type')),
            R(count=g.add(F(state, 'count'), I(1)), valid=g.both(F(state, 'valid'), c('media-type-is', F(header, 'value'), I('application/json')))), state))
    g.fn('json-media', {'headers': '@Headers'}, 'bool', lambda headers:
         LET([('media', g.fold('@Header', '@Media', headers, R(count=I(0), valid=I(True)), 'media-step'))],
             g.both(g.eq(F(L('media'), 'count'), I(1)), F(L('media'), 'valid'))))
    g.fn('key-digit', {'index': 'i64'}, 'text', lambda index: digit_selector(g, index))
    g.fn('key-prefix', {'token': 'text', 'prefix': 'text', 'length': 'i64', 'choice': 'i64'}, 'bool', lambda token, prefix, length, choice:
         IF(g.eq(length, I(64)), g.text_eq(token, prefix),
            IF(g.less(choice, I(16)), LET([('next', g.concat(prefix, c('$key-digit', choice)))],
               IF(c('text-starts-with', token, L('next')), c('$key-prefix', token, L('next'), g.add(length, I(1)), I(0)),
                  c('$key-prefix', token, prefix, length, g.add(choice, I(1))))), I(False))))
    g.fn('valid-key', {'token': 'text'}, 'bool', lambda token:
         g.both(g.eq(c('bytes-length', c('bytes-from-text', token)), I(64)), c('$key-prefix', token, I(''), I(0), I(0))))
    for name, value, expected in [('valid', '0123456789abcdef' * 4, True), ('uppercase', 'A' + '0' * 63, False),
                                   ('space', '0' * 32 + ' ' + '0' * 31, False), ('unicode', 'a' * 62 + 'é', False)]:
        a.test('recovery-key-' + name, c('$valid-key', I(value)), I(expected))
    g.fn('secret-key', {'token': 'text'}, 'text', lambda token:
         g.concat(I('auth:'), c('bytes-to-hex', c('bytes-blake3', c('bytes-from-text', token)))))
    g.fn('new-secret', {}, 'text', c('bytes-to-hex', a.cap('random', 'SecureRandom', 'bytes', I(32))), ('random',))
    g.fn('authenticate', {'headers': '@Headers'}, 'i64', lambda headers:
         LET([('token', c('bearer-token', headers))],
             IF(g.eq(c('text-length', L('token')), I(64)), LET([('entries', a.get(c('$secret-key', L('token'))))],
                IF(g.eq(g.length(L('entries'), '@DataEntry'), I(1)), c('data-decode-or',
                   a.nominal_field(g.get(L('entries'), I(0), '@DataEntry'), 'DataEntry', 'value'), I(-1), types=('i64',)), I(-1))), I(-1))), ('data',))
    g.fn('read-world', {'tick': 'i64'}, '@WorldRead', lambda tick:
         LET([('entries', a.get(I('world')))],
             IF(g.eq(g.length(L('entries'), '@DataEntry'), I(0)),
                R(exists=I(False), valid=I(True), world=c('$empty-world', tick), expectation=a.variant('DataExpectation', 'Missing')),
                LET([('entry', g.get(L('entries'), I(0), '@DataEntry')),
                     ('decoded', c('data-decode-or', a.nominal_field(L('entry'), 'DataEntry', 'value'),
                                   g.copy('World', c('$empty-world', tick), version=I(-1)), types=('@World',)))],
                    R(exists=I(True), valid=g.both(g.eq(F(L('decoded'), 'version'), I(1)),
                         g.le(I(0), F(L('decoded'), 'tick')), g.le(g.length(F(L('decoded'), 'colonies'), '@Colony'), I(64))),
                      world=L('decoded'), expectation=a.variant('DataExpectation', 'Exact', a.nominal_field(L('entry'), 'DataEntry', 'revision')))))), ('data',))
    g.fn('envelope', {'world': '@World', 'id': 'i64', 'now': 'i64'}, '@Response', lambda world, identifier, now:
         a.json_response(R(me=identifier, world=world, now_ms=now,
              backlog_ticks=g.high(I(0), g.sub(g.div(now, I(10000)), F(world, 'tick')))), '@Envelope'))
    g.fn('persist-envelope', {'read': '@WorldRead', 'world': '@World', 'id': 'i64', 'now': 'i64'}, '@Response', lambda read, world, identifier, now:
         IF(a.put(I('world'), world, '@World', F(read, 'expectation')), c('$envelope', world, identifier, now), error(409, 'transaction_conflict')), ('data',))

    def authenticated(request, expression, effects, name):
        body = LET([('id', c('$authenticate', F(request, 'headers')))],
             IF(g.less(I(0), L('id')),
                LET([('now', a.cap('clock', 'WallClock', 'utc-milliseconds')),
                     ('read', c('$read-world', g.div(L('now'), I(10000))))],
                  IF(F(L('read'), 'valid'),
                     IF(g.le(I(0), c('$find-colony-index', F(F(L('read'), 'world'), 'colonies'), L('id'), I(0))),
                        expression(L('read'), L('id'), L('now')), error(401, 'unauthorized')), error(500, 'persistence_shape'))),
                error(401, 'unauthorized')))
        return a.transaction(body)

    def sync(read, identifier, now):
        return LET([('old', F(read, 'world')),
                    ('budget', g.high(I(1), g.div(I(12), g.high(I(1), g.length(F(L('old'), 'colonies'), '@Colony'))))),
                    ('new', c('$advance-world', L('old'), g.div(now, I(10000)), L('budget')))],
                   IF(g.eq(F(L('old'), 'tick'), F(L('new'), 'tick')), c('$envelope', L('old'), identifier, now),
                      c('$persist-envelope', read, L('new'), identifier, now)))
    g.fn('http-view', {'request': '@Request'}, '@Response', lambda request:
         authenticated(request, lambda read, identifier, now: c('$envelope', F(read, 'world'), identifier, now), (), 'view'), ('data', 'clock'))
    a.port('view', 'http-view', method='GET', path='/api/view')
    g.fn('http-sync', {'request': '@Request'}, '@Response', lambda request:
         authenticated(request, sync, (), 'sync'), ('data', 'clock'))
    a.port('sync', 'http-sync', method='POST', path='/api/sync')

    def accept_new(read, identifier, now, name, token):
        return LET([('colony', c('$new-colony', identifier, name, g.div(now, I(10000)))),
                    ('world', g.copy('World', F(read, 'world'), next_id=g.add(identifier, I(1)),
                              colonies=g.append(F(F(read, 'world'), 'colonies'), L('colony'), '@Colony')))],
            IF(a.put(c('$secret-key', token), identifier, 'i64', a.variant('DataExpectation', 'Missing')),
               IF(a.put(I('world'), L('world'), '@World', F(read, 'expectation')),
                  a.json_response(R(id=identifier, token=token), '@Joined', status=201), error(409, 'transaction_conflict')),
               error(409, 'transaction_conflict')))
    g.fn('join-world', {'read': '@WorldRead', 'id': 'i64', 'now': 'i64', 'name': 'text', 'token': 'text'}, '@Response', accept_new, ('data',))

    def registration(read, now, name, token):
        return LET([('auth', a.get(c('$secret-key', token)))],
            IF(g.eq(g.length(L('auth'), '@DataEntry'), I(1)),
               LET([('id', c('data-decode-or', a.nominal_field(g.get(L('auth'), I(0), '@DataEntry'), 'DataEntry', 'value'), I(-1), types=('i64',)))],
                   IF(g.less(I(0), L('id')), a.json_response(R(id=L('id'), token=token), '@Joined'), error(500, 'persistence_shape'))),
               IF(g.less(g.length(F(F(read, 'world'), 'colonies'), '@Colony'), I(64)),
                  c('$join-world', read, F(F(read, 'world'), 'next_id'), now, name, token), error(409, 'world_full'))))
    g.fn('register-colony', {'read': '@WorldRead', 'now': 'i64', 'name': 'text', 'token': 'text'}, '@Response', registration, ('data',))

    def join(request):
        # The browser keeps a 256-bit random key BEFORE sending this idempotent registration.
        parsed = c('json-decode-or', a.cap('streams', 'ByteStream', 'read-all', F(request, 'body'), I(4096)), R(name=I(''), token=I('')), types=('@Join',))
        return IF(c('$json-media', F(request, 'headers')),
            LET([('parsed', parsed)], IF(F(L('parsed'), 'valid'),
                LET([('name', F(F(L('parsed'), 'value'), 'name')), ('token', F(F(L('parsed'), 'value'), 'token'))],
                  IF(g.both(g.less(I(0), c('text-length', L('name'))), g.le(c('text-length', L('name')), I(32)),
                            c('$valid-key', L('token'))),
                    IF(c('$schema-ready'),
                      LET([('now', a.cap('clock', 'WallClock', 'utc-milliseconds')), ('read', c('$read-world', g.div(L('now'), I(10000))))],
                          IF(F(L('read'), 'valid'), c('$register-colony', L('read'), L('now'), L('name'), L('token')), error(500, 'persistence_shape'))),
                      error(500, 'schema_mismatch')), error(400, 'invalid_registration'))), error(400, 'invalid_json'))),
            error(415, 'content_type'))
    g.fn('http-join', {'request': '@Request'}, '@Response', lambda request: a.transaction(join(request)), ('data', 'streams', 'clock'))
    a.port('join', 'http-join', method='POST', path='/api/join')

    def sequenced(read, identifier, now, action):
        return LET([('world', F(read, 'world')), ('index', c('$find-colony-index', F(L('world'), 'colonies'), identifier, I(0))),
                    ('colony', g.get(F(L('world'), 'colonies'), L('index'), '@Colony')),
                    ('intent', c('bytes-to-hex', c('bytes-blake3', c('data-encode', action, types=('@Action',)))))],
            IF(g.both(g.le(F(action, 'sequence'), F(L('colony'), 'sequence')), g.text_eq(g.concat(g.concat(g.decimal(F(action, 'sequence')), I(':')), L('intent')), g.mget(F(L('colony'), 'receipts'), g.decimal(g.mod(F(action, 'sequence'), I(64))), I(''), 'text'))),
               c('$envelope', L('world'), identifier, now),
               IF(g.eq(F(action, 'sequence'), g.add(F(L('colony'), 'sequence'), I(1))),
                 IF(g.le(g.div(now, I(10000)), F(L('world'), 'tick')),
                   LET([('result', c('$dispatch-action', L('world'), L('colony'), action, now))],
                       IF(F(L('result'), 'ok'),
                         LET([('new-world', F(L('result'), 'world')),
                              ('new-index', c('$find-colony-index', F(L('new-world'), 'colonies'), identifier, I(0))),
                              ('new-colony', g.get(F(L('new-world'), 'colonies'), L('new-index'), '@Colony')),
                              ('signed', g.copy('Colony', L('new-colony'), sequence=F(action, 'sequence'), last_intent=L('intent'), receipts=g.mset(F(L('new-colony'), 'receipts'), g.decimal(g.mod(F(action, 'sequence'), I(64))), g.concat(g.concat(g.decimal(F(action, 'sequence')), I(':')), L('intent')), 'text'))),
                              ('committed', c('$replace-colony', L('new-world'), L('signed')))],
                             c('$persist-envelope', read, L('committed'), identifier, now)),
                         error(400, F(L('result'), 'error')))), error(409, 'catchup_required')), error(409, 'sequence_conflict'))))
    g.fn('sequence-action', {'read': '@WorldRead', 'id': 'i64', 'now': 'i64', 'action': '@Action'}, '@Response', sequenced, ('data',))
    def action(request):
        def apply(read, identifier, now):
            fallback = R(op=I(''), sequence=I(0), index=I(0), value=I(0), x=I(0), y=I(0), text=I(''))
            return IF(c('$json-media', F(request, 'headers')),
                LET([('parsed', c('json-decode-or', a.cap('streams', 'ByteStream', 'read-all', F(request, 'body'), I(4096)), fallback, types=('@Action',)))],
                    IF(F(L('parsed'), 'valid'),
                       IF(c('$action-bounds', F(L('parsed'), 'value')), c('$sequence-action', read, identifier, now, F(L('parsed'), 'value')),
                          error(400, 'invalid_action')), error(400, 'invalid_json'))), error(415, 'content_type'))
        return authenticated(request, apply, (), 'action')
    g.fn('http-action', {'request': '@Request'}, '@Response', action, ('data', 'clock', 'streams'))
    a.port('action', 'http-action', method='POST', path='/api/action')
    health = {'ok': True, 'name': 'Orbloam', 'runtime': 'lkjscript 0.1.38', 'schema': 'orbloam-world-v1'}
    for name, path, content in [('health', '/health', health), ('catalog', '/api/catalog', CATALOG)]:
        g.fn('http-' + name, {'request': '@Request'}, '@Response', a.response(200, c('bytes-from-text', I(json.dumps(content, ensure_ascii=False, separators=(',', ':'))))))
        a.port(name, 'http-' + name, method='GET', path=path)
    root = Path(__file__).resolve().parents[1]
    for index, file in enumerate(sorted((root / 'web').glob('*'))):
        if not file.is_file() or file.suffix not in ['.html', '.js', '.css']:
            continue
        mime = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8'}[file.suffix]
        name = 'asset-' + str(index)
        g.fn(name, {'request': '@Request'}, '@Response', a.response(200, c('bytes-from-text', I(file.read_text())), mime))
        a.port(name, name, method='GET', path='/' if file.name == 'index.html' else '/' + file.name)
        if file.name == 'index.html':
            a.port(name + '-index', name, method='GET', path='/index.html')
    operator_fixture(g)


def operator_fixture(g):
    """An explicit local command, never an HTTP route; refuses an existing world."""
    a, c = g.a, g.c
    def transaction_text(body):
        outcome, reason = a.ref('TransactionOutcome'), a.ref('TransactionAbortReason')
        committed, aborted = a.ref('Committed', 'TransactionOutcome'), a.ref('Aborted', 'TransactionOutcome')
        condition, conflict = a.ref('ConditionFailed', 'TransactionAbortReason'), a.ref('Conflict', 'TransactionAbortReason')
        return f'(match (transaction-outcome $data (types text) (outcome {outcome} {reason} {committed} {aborted} {condition} {conflict}) (binding fixture) {body}) (arm {committed} (payload complete text) (local complete)) (arm {aborted} (payload reason @TransactionAbortReason) (text "fixture refused: transaction conflict")))'
    def fixture(population, age):
        def building(kind):
            return R(id=I(kind + 1), kind=I(kind), recipe=I(kind * 9), x=I(-256 + (kind % 4) * 32), y=I(-32 + (kind // 4) * 64),
                     health=I(100), progress=I(0), produced=I(0), enabled=I(True), status=I('workers'))
        inventory = g.map(**{key: 10000 for key in RAW}, plank=400, ingot=400)
        ready = LET([('now', a.cap('clock', 'WallClock', 'utc-milliseconds')), ('tick', g.sub(g.div(L('now'), I(10000)), age)),
                     ('read', c('$read-world', L('tick')))],
            IF(F(L('read'), 'exists'), I('fixture refused: existing world'),
              IF(c('$schema-ready'),
                LET([('token', c('$new-secret')), ('base', c('$new-colony', I(1), I('Benchmark colony'), L('tick'))),
                     ('colony', g.copy('Colony', L('base'), cohorts=g.list('@Cohort', R(first=I(0), count=population, start=g.sub(L('tick'), g.sub(population, I(1))))),
                       research=g.map(**{'1': 8, '2': 4, '3': 8, '4': 8, '5': 8, '6': 4}), inventory=inventory,
                       buildings=g.list('@Building', *(building(kind) for kind in range(8))), next_building=I(9), essence=I(100000), experience=I(1000))),
                     ('world', g.copy('World', F(L('read'), 'world'), next_id=I(2), colonies=g.list('@Colony', L('colony'))))],
                    IF(a.put(c('$secret-key', L('token')), I(1), 'i64', a.variant('DataExpectation', 'Missing')),
                       IF(a.put(I('world'), L('world'), '@World', F(L('read'), 'expectation')),
                          g.concat(I('orbloam-fixture-token:'), L('token')), I('fixture refused: world conflict')), I('fixture refused: credential conflict'))),
                I('fixture refused: schema mismatch'))))
        return transaction_text(IF(g.both(g.le(I(1), population), g.le(population, I(4096)), g.le(I(0), age), g.le(age, I(8640))), ready,
                                   I('fixture refused: invalid arguments')))
    g.fn('fixture-create', {'population': 'i64', 'age-ticks': 'i64'}, 'text', fixture, ('data', 'clock', 'random'))
    a.port('fixture-create', 'fixture-create', target='fixture-create')


def digit_selector(g, index):
    def branch(lo, hi):
        if hi - lo == 1:
            return I('0123456789abcdef'[lo])
        mid = (lo + hi) // 2
        return IF(g.less(index, I(mid)), branch(lo, mid), branch(mid, hi))
    return branch(0, 16)
