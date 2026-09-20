#!/usr/bin/env python3
"""Real native HTTP + browser UI. Optional explicit blank-document test bridge.

The bridge is only for environments that deny navigation. It tests served client
code against the real native application, not real browser CORS/CSP/TLS/storage.
It never substitutes canned worlds, simulation, or game actions in the frontend.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import http.client
import json
import math
from pathlib import Path
import sys
import time
import traceback
from urllib.parse import urlsplit

from native import NativeApp, ROOT, ARTIFACT, BINARY, sha256, redact
from playwright.sync_api import sync_playwright

ASSETS = ['index.html', 'styles.css', 'api.js', 'world.js', 'research.js', 'client.js']


def bind_bridge(page, app, assets, fault):
    """Run fetched bytes in an opaque document; forward only this native origin."""
    expected = urlsplit(app.base)
    def raw_http(argument):
        url = urlsplit(argument['url'])
        if url.scheme != expected.scheme or url.netloc != expected.netloc:
            raise RuntimeError('Bridge rejected a foreign authority')
        connection = http.client.HTTPConnection('127.0.0.1', app.port, timeout=40)
        try:
            body = argument.get('body')
            if isinstance(body, str):
                body = body.encode('utf-8')
            connection.request(argument['method'], url.path + ('?' + url.query if url.query else ''), body=body, headers=argument['headers'])
            response = connection.getresponse()
            payload = response.read()
            if fault.get('drop_action') and url.path == '/api/action' and response.status == 200:
                fault['drop_action'] = False
                fault['dropped_after_commit'] = True
                raise RuntimeError('Intentional test: response lost after the native server committed')
            return {'status': response.status, 'headers': dict(response.getheaders()), 'body': base64.b64encode(payload).decode()}
        finally:
            connection.close()
    page.expose_function('_orbloamTestHTTP', raw_http)
    html = assets['index.html'].replace('<head>', '<head><base href="' + app.base + '">')
    html = html.replace('<link rel="stylesheet" href="./styles.css">', '').replace('<script type="module" src="./client.js"></script>', '')
    page.set_content(html)
    page.add_style_tag(content=assets['styles.css'])
    page.evaluate('''async ({assets}) => {
      // A separately declared test storage adapter; not a browser persistence proof.
      const storage = new Map();
      Object.defineProperty(window, 'localStorage', {value: {
        getItem: key => storage.has(key) ? storage.get(key) : null,
        setItem: (key,value) => storage.set(key, String(value)),
        removeItem: key => storage.delete(key)
      }});
      window.fetch = async (input, init={}) => {
        const reply = await window._orbloamTestHTTP({url: new URL(String(input),document.baseURI).href,
          method: init.method || 'GET', headers: Object.fromEntries(new Headers(init.headers || {})), body: init.body ?? null});
        return new Response(Uint8Array.from(atob(reply.body), x=>x.charCodeAt(0)), {status:reply.status,headers:reply.headers});
      };
      const urls = {};
      for (const name of ['world.js','api.js','research.js','client.js']) {
        let source = assets[name];
        for (const [module,url] of Object.entries(urls)) source = source.replaceAll("'./"+module+"'", JSON.stringify(url));
        urls[name] = URL.createObjectURL(new Blob([source],{type:'text/javascript'}));
      }
      await import(urls['client.js']);
    }''', {'assets': assets})


def browser_suite(bridge_if_blocked, output):
    screenshots = output / 'screenshots'
    screenshots.mkdir(parents=True, exist_ok=True)
    report = {'schema': 'orbloam-browser-acceptance-v1', 'artifact_sha256': sha256(ARTIFACT),
              'runtime_sha256': sha256(BINARY), 'status': 'failed', 'mode': 'direct-navigation', 'page_errors': []}
    app = NativeApp()
    fault = {}
    with app, sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path='/usr/bin/chromium', headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage'])
        report['browser'] = browser.version
        assets = {name: app.expect(200, name).decode() for name in ASSETS}
        report['served_asset_sha256'] = {name: hashlib.sha256(value.encode()).hexdigest() for name,value in assets.items()}
        def make_page(width=1440,height=960):
            context = browser.new_context(viewport={'width':width,'height':height},device_scale_factor=1)
            page = context.new_page()
            page.on('pageerror', lambda error: report['page_errors'].append(redact(str(error))))
            if report['mode'] == 'blank-document-native-http-bridge':
                bind_bridge(page, app, assets, fault)
            else:
                try:
                    page.goto(app.base, wait_until='domcontentloaded', timeout=30000)
                except Exception as error:
                    report['navigation_error'] = redact(str(error)).split('Call log:')[0]
                    if not bridge_if_blocked or 'ERR_BLOCKED_BY_ADMINISTRATOR' not in str(error):
                        raise
                    page.close()
                    page = context.new_page()
                    page.on('pageerror', lambda error: report['page_errors'].append(redact(str(error))))
                    report['mode'] = 'blank-document-native-http-bridge'
                    report['nonclaims'] = ['normal browser navigation', 'CSP enforcement', 'CORS enforcement', 'TLS',
                                         'native localStorage persistence/permissions', 'clipboard permissions', 'external reverse proxy']
                    bind_bridge(page, app, assets, fault)
            page.wait_for_function('typeof window.orbloamDiagnostics === "function"',timeout=30000)
            return page
        def entered(page):
            page.wait_for_function("document.querySelector('#auth').classList.contains('hidden')",timeout=30000)
            page.wait_for_function('window.orbloamDiagnostics().backlogTicks === 0',timeout=30000)
        try:
            page = make_page()
            page.screenshot(path=str(screenshots/'welcome.png'))
            page.locator('#nickname').fill('こもれび')
            page.locator('#join-form button').click()
            entered(page)
            page.locator('#dismiss-key').click()
            page.locator('#key-button').click()
            token = page.locator('#key-value').input_value()
            assert len(token) == 64 and page.locator('#key-value').get_attribute('type') == 'password'
            page.locator('[data-close="key-dialog"]').click()
            assert '80' in page.locator('#panel-content').inner_text(), 'Native inventory map was not decoded'
            # Actual UI -> actual native research command.
            page.locator('#open-research').click()
            angle = -math.pi / 2 + math.sin(1.618) * .09
            page.mouse.click(570 + math.cos(angle) * 135 * .8, 528 + math.sin(angle) * 135 * .8)
            page.get_by_role('button',name='この研究を解放する',exact=True).click()
            page.wait_for_function("document.querySelector('#research-progress').textContent === '1 / 96'")
            assert next(c for c in app.view(token)['world']['colonies'] if c['id']==1)['research']['0']==1
            page.locator('#research-fit').click()
            page.screenshot(path=str(screenshots/'research.png'))
            page.locator('#research-close').click()
            # Build through the native action API via real place-selection controls.
            page.locator('#build-mode').click()
            page.get_by_role('button',name='場所を選んで建てる').first.click()
            page.mouse.click(800, 500)
            page.wait_for_function("document.querySelector('#mode-hint').classList.contains('hidden')")
            state = app.view(token)
            mine = next(c for c in state['world']['colonies'] if c['id']==state['me'])
            assert len(mine['buildings']) == 1
            page.locator('#inspect-mode').click()
            # Actual movement. In bridge mode deliberately lose only the first committed reply.
            if report['mode'] == 'blank-document-native-http-bridge':
                fault['drop_action'] = True
            page.locator('#move-mode').click()
            page.mouse.click(785, 620)
            if report['mode'] == 'blank-document-native-http-bridge':
                page.wait_for_function("!document.querySelector('#pending').classList.contains('hidden') && window.orbloamDiagnostics().maximumGameRequests === 1")
                page.wait_for_timeout(500)
                before_retry = app.view(token)
                sequence = next(c for c in before_retry['world']['colonies'] if c['id']==before_retry['me'])['sequence']
                page.locator('#retry-pending').click()
                page.wait_for_function("document.querySelector('#pending').classList.contains('hidden')",timeout=30000)
                assert next(c for c in app.view(token)['world']['colonies'] if c['id']==1)['sequence']==sequence
                assert fault.get('dropped_after_commit')
                report['lost_action_response_replayed_once'] = True
            else:
                page.wait_for_function("document.querySelector('#mode-hint').classList.contains('hidden')")
            page.locator('#inspect-mode').click()
            page.locator('#inventory-button').click()
            page.screenshot(path=str(screenshots/'world.png'))
            other = make_page()
            other.locator('#nickname').fill('<script>neighbor</script>')
            other.locator('#join-form button').click()
            entered(other)
            other.locator('#dismiss-key').click()
            other.locator('[data-tab="neighbors"]').click()
            assert 'こもれび' in other.locator('#panel-content').inner_text()
            page.wait_for_function("document.querySelector('#colony-count').textContent.startsWith('2')",timeout=10000)
            page.locator('[data-tab="neighbors"]').click()
            assert '<script>neighbor</script>' in page.locator('#panel-content').inner_text()
            assert page.locator('#panel-content script').count() == 0
            # Extreme zoom remains finite and explicit about sampled far views.
            for _ in range(13):
                page.locator('#zoom-out').click()
            page.wait_for_timeout(150)
            assert page.evaluate('window.orbloamDiagnostics().camera.zoom') >= .025
            page.screenshot(path=str(screenshots/'survey.png'))
            mobile = make_page(390,844)
            mobile.locator('details summary').click()
            mobile.locator('#recovery-key').fill(token)
            mobile.locator('#recover-form button').click()
            entered(mobile)
            mobile.locator('#close-sidebar').click()
            assert mobile.locator('#colony-name').inner_text() == 'こもれび'
            assert mobile.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
            mobile.screenshot(path=str(screenshots/'mobile.png'))
            mobile.locator('#open-research').click()
            mobile.locator('#research-fit').click()
            mobile.screenshot(path=str(screenshots/'mobile-research.png'))
            for candidate in [page,other,mobile]:
                diagnostics = candidate.evaluate('window.orbloamDiagnostics()')
                assert diagnostics['maximumGameRequests'] == 1
                assert diagnostics['frames'] > 0
                assert diagnostics['backlogTicks'] == 0
            assert not report['page_errors'], report['page_errors']
            report['observations'] = {'desktop': [1440,960], 'mobile': [390,844], 'native_registration': True,
                'real_research_purchase': True, 'real_build_and_move': True, 'two_identities_one_world': True,
                'mobile_recovery_same_core': True, 'untrusted_name_is_text': True, 'maximum_game_requests': 1,
                'finite_extreme_zoom': True, 'mobile_no_horizontal_overflow': True}
            report['status'] = 'passed'
        except Exception as error:
            report['error'] = redact(str(error))[:5000]
            report['traceback'] = redact(traceback.format_exc())[-6000:]
            try:
                page.screenshot(path=str(screenshots/'failure.png'))
            except Exception:
                pass
        finally:
            browser.close()
    app.verify()
    if sha256(ARTIFACT) != report['artifact_sha256']:
        report['status'] = 'failed'
        report['artifact_changed_during_test'] = True
    output.mkdir(parents=True,exist_ok=True)
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return report['status']=='passed'


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bridge-if-blocked',action='store_true')
    parser.add_argument('--output',type=Path,default=ROOT/'evidence/browser')
    args=parser.parse_args()
    sys.exit(0 if browser_suite(args.bridge_if_blocked,args.output) else 1)
