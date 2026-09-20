#!/usr/bin/env python3
"""Exercise the exact artifact through native commands, HTTP, restart and logical recovery."""
from __future__ import annotations
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import secrets
import shutil
import sys
import time
import traceback

from native import NativeApp, BINARY, ARTIFACT, ROOT, native, sha256, redact, execution_value
from oracle import assert_probe, deaths_between


def owner(state, identifier=None):
    return next(c for c in state['world']['colonies'] if c['id'] == (identifier or state['me']))


def action(op, sequence, **fields):
    return dict(op=op, sequence=sequence, index=0, value=0, x=0, y=0, text='', **{}) | fields


def http_journey():
    app = NativeApp()
    tokens = []
    with app:
        health = app.expect(200, 'health')
        assert health['name'] == 'Orbloam' and health['runtime'] == 'lkjscript 0.1.38'
        catalogue = app.expect(200, 'api/catalog')
        assert len(catalogue['recipes']) == 72 and len(catalogue['research']) == 96
        for name in ['index.html', 'api.js', 'client.js', 'world.js', 'research.js', 'styles.css']:
            status, body, headers = app.request(name)
            assert status == 200 and body == (ROOT / 'web' / name).read_bytes(), ('embedded-asset', name)
            assert headers.get('X-Content-Type-Options', headers.get('x-content-type-options')) == 'nosniff'
            csp = headers.get('Content-Security-Policy', headers.get('content-security-policy', ''))
            assert "script-src 'self'" in csp and 'unsafe-eval' not in csp
        assert app.expect(404, 'api/operator', 'POST', {}) == b''
        app.expect(401, 'api/view')
        app.expect(401, 'api/sync', 'POST', {}, secrets.token_hex(32))
        token, first_id = app.join('新しいコロニー')
        tokens.append(token)
        repeated = app.expect(200, 'api/join', 'POST', {'name': 'A different nickname', 'token': token})
        assert repeated['id'] == first_id and repeated['token'] == token
        state = app.view(token)
        assert len(state['world']['colonies']) == 1 and owner(state)['name'] == '新しいコロニー'
        second, second_id = app.join('<script>not executable</script>')
        tokens.append(second)
        assert second_id != first_id
        # Strict input rejects without creating another identity or changing the world.
        before = app.view(token)['world']
        for bad in ['0' * 63, 'A' + '0' * 63, '0' * 32 + ' ' + '0' * 31, 'a' * 62 + 'é']:
            app.expect(400, 'api/join', 'POST', {'name': 'invalid key', 'token': bad})
        for raw in [b'{"name":"first","name":"second","token":"' + b'0' * 64 + b'"}',
                    b'{"name":"extra","token":"' + b'0' * 64 + b'","extra":1}',
                    b'{"name":"trailing","token":"' + b'0' * 64 + b'"} trailing']:
            app.expect(400, 'api/join', 'POST', raw=raw, headers={'Content-Type': 'application/json'})
        app.expect(415, 'api/join', 'POST', raw=b'{}', headers={'Content-Type': 'text/plain'})
        assert app.view(token)['world'] == before
        # Different Host/authority, same store and identity; not an external-network claim.
        assert app.request('api/view', token=token, host='localhost')[1]['me'] == first_id

        moved, move = app.action(token, 'move', x=-210, y=12)
        assert owner(moved)['to_x'] == -210 and owner(moved)['to_y'] == 12
        renamed, rename = app.action(token, 'rename', text='Shared grove')
        replay = app.expect(200, 'api/action', 'POST', move, token)
        assert owner(replay)['sequence'] == owner(renamed)['sequence'] and owner(replay)['name'] == 'Shared grove'
        app.expect(409, 'api/action', 'POST', dict(move, x=-200), token)
        state = app.sync(token)
        seq = owner(state)['sequence'] + 1
        app.expect(400, 'api/action', 'POST', action('move', seq, x=1000001), token)
        app.expect(400, 'api/action', 'POST', action('research', seq, index=1), token)
        assert owner(app.view(token))['sequence'] == seq - 1

        grown, _ = app.action(token, 'research', index=0)
        previous = owner(app.before_action)
        assert owner(grown)['essence'] == previous['essence'] - catalogue['research'][0]['essence']
        assert owner(grown)['inventory']['timber'] == previous['inventory']['timber'] - 20
        assert sum(c['count'] for c in owner(grown)['cohorts']) == 64
        industrial, _ = app.action(token, 'research', index=36)
        assert owner(industrial)['research']['3'] == 1
        built, building_action = app.action(token, 'build', index=0, value=0, x=-190, y=20)
        previous = owner(app.before_action)
        building = owner(built)['buildings'][0]
        assert owner(built)['inventory']['timber'] == previous['inventory']['timber'] - 30
        assert owner(built)['inventory']['stone'] == previous['inventory']['stone'] - 20
        assert building['kind'] == 0 and building['x'] == -190
        snapshot = app.sync(second)
        app.expect(400, 'api/action', 'POST', action('repair', owner(snapshot)['sequence'] + 1, index=building['id']), second)
        paused, _ = app.action(token, 'pause', index=building['id'], value=0)
        assert owner(paused)['buildings'][0]['enabled'] is False
        recipe, _ = app.action(token, 'recipe', index=building['id'], value=1)
        assert owner(recipe)['buildings'][0]['recipe'] == 1
        resumed, _ = app.action(token, 'pause', index=building['id'], value=1)
        assert owner(resumed)['buildings'][0]['enabled'] is True

        gift, gift_action = app.action(token, 'transfer', index=second_id, value=5, text='timber')
        assert owner(gift)['inventory']['timber'] == owner(app.before_action)['inventory']['timber'] - 5
        assert owner(gift, second_id)['inventory']['timber'] == owner(app.before_action, second_id)['inventory']['timber'] + 5
        app.action(token, 'rename', text='Shared grove after gift')
        before_replay = app.view(token)['world']
        assert app.expect(200, 'api/action', 'POST', gift_action, token)['world'] == before_replay
        # Concurrent identical commands have one effect, and both callers can obtain an acknowledgement.
        state = app.sync(token)
        intent = action('rename', owner(state)['sequence'] + 1, text='One committed rename')
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            replies = list(pool.map(lambda _: app.request('api/action', 'POST', intent, token), range(2)))
        if any(status == 409 and value.get('error') == 'catchup_required' for status, value, _ in replies):
            app.sync(token)
            replies = [app.request('api/action', 'POST', intent, token) for _ in range(2)]
        assert all(status == 200 for status, _, _ in replies)
        assert owner(app.view(token))['sequence'] == intent['sequence']
        repaired, _ = app.action(token, 'repair', index=building['id'])
        assert owner(repaired)['buildings'][0]['health'] == 100
        assert owner(repaired)['inventory']['stone'] == owner(app.before_action)['inventory']['stone'] - 5
        dismantled, _ = app.action(token, 'dismantle', index=building['id'])
        assert not owner(dismantled)['buildings']
        assert owner(dismantled)['inventory']['timber'] == owner(app.before_action)['inventory']['timber'] + 7
        saved = app.view(token)['world']
        public_bytes = json.dumps(saved).encode()
        assert all(t.encode() not in public_bytes for t in tokens)
    verification = app.verify()
    with app:
        assert app.view(token)['world'] == saved
    backup = app.root / 'snapshot.lkjd'
    native('data', 'backup', '--root', app.root / 'data', '--output', backup)
    assert all(t.encode() not in backup.read_bytes() for t in tokens)
    restored_root = app.root / 'restored'
    restored_root.mkdir()
    native('data', 'restore', '--backup', backup, '--root', restored_root / 'data')
    restored = NativeApp(root=restored_root, initialize=False)
    with restored:
        assert restored.view(token)['world'] == saved
        assert restored.view(second)['me'] == second_id
    restored.verify()
    return {'http_observations': len(app.measurements), 'registered_cores': 2, 'registration_retry_same_identity': True,
            'owned_commands': ['move', 'rename', 'research', 'build', 'pause', 'recipe', 'transfer', 'repair', 'dismantle'],
            'replay_after_later_action': True, 'concurrent_identical_intent_once': True,
            'restart_equal': True, 'logical_restore_equal': True, 'credentials_absent_from_public_world_and_backup': True,
            'data_verified': 'status=success' in verification}


def native_oracles():
    app = NativeApp()
    populations = json.loads(execution_value(app.command('diagnostic-page', [0])))
    report = json.loads(execution_value(app.command('diagnostic-page', [1])))
    report['populations'] = populations
    report['machines'] = []
    for index in range(2, 20):
        report['machines'].extend(json.loads(execution_value(app.command('diagnostic-page', [index]))))
    with app:
        catalogue = app.expect(200, 'api/catalog')
    result = assert_probe(report, catalogue)
    app.verify()
    return result


def one_hour_catchup():
    app = NativeApp()
    token = app.seed(512, 360)
    with app:
        before = app.view(token)
        started = time.monotonic()
        after = app.sync(token, attempts=100)
        elapsed = time.monotonic() - started
        first, last = owner(before), owner(after)
        delta = after['world']['tick'] - before['world']['tick']
        deaths = deaths_between(first['cohorts'], before['world']['tick'], after['world']['tick'])
        assert last['deaths'] - first['deaths'] == deaths
        assert last['essence'] == first['essence'] + 14 * deaths
        for building in last['buildings']:
            assert building['produced'] == (delta // 3) * (3 if building['kind'] == 7 else 6), building
            assert building['health'] == 100 and building['progress'] == delta % 3
        assert len(after['world']['nodes']) <= 4096
        assert all(0 <= n['stock'] <= 180 + 30 * n['tier'] for n in after['world']['nodes'].values())
        assert after['backlog_ticks'] == 0
        # Exact replay and a real post-load command, not merely a successful state projection.
        state, intent = app.action(token, 'move', x=-190, y=17)
        assert owner(state)['to_x'] == -190
        assert app.expect(200, 'api/action', 'POST', intent, token)['world'] == state['world']
    app.verify()
    # A second local fixture request must never overwrite a populated store.
    refused = execution_value(app.command('fixture-create', [16, 0]))
    assert 'refused: existing world' in refused
    return {'fixture_population': 512, 'fixture_workshops': 8, 'requested_absence_ticks': 360,
            'processed_ticks': delta, 'calculated_deaths': deaths, 'actual_deaths': last['deaths'] - first['deaths'],
            'catchup_wall_seconds': elapsed, 'final_backlog_ticks': 0, 'all_eight_processing_totals_exact': True,
            'post_load_move_and_replay': True, 'existing_world_not_overwritten': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'evidence/acceptance.json')
    options = parser.parse_args()
    report = {'schema': 'orbloam-native-acceptance-v1', 'artifact_sha256': sha256(ARTIFACT),
              'runtime_sha256': sha256(BINARY), 'groups': {}, 'status': 'passed'}
    for name, test in [('http-and-recovery', http_journey), ('independent-native-oracles', native_oracles), ('one-hour-exact-catchup', one_hour_catchup)]:
        print('RUN', name, flush=True)
        began = time.monotonic()
        try:
            facts = test()
            report['groups'][name] = {'status': 'passed', 'elapsed_seconds': time.monotonic() - began, 'observations': facts}
            print('PASS', name, flush=True)
        except Exception as error:
            report['status'] = 'failed'
            report['groups'][name] = {'status': 'failed', 'elapsed_seconds': time.monotonic() - began,
                                     'error': redact(str(error))[:6000], 'traceback': redact(traceback.format_exc())[-5000:]}
            print('FAIL', name, redact(str(error))[:6000], flush=True)
    if sha256(ARTIFACT) != report['artifact_sha256']:
        report['status'] = 'failed'
        report['artifact_changed_during_tests'] = True
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('RESULT', report['status'], options.output, flush=True)
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
