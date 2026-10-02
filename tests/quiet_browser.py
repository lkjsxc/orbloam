#!/usr/bin/env python3
"""Quiet-world UI against the real native app, with an explicitly marked fallback bridge."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import time
import traceback
from playwright.sync_api import sync_playwright
from native import NativeApp, ROOT, ARTIFACT, BINARY, sha256, redact
from browser import bind_bridge, ASSETS


def main(allow_bridge):
    output = ROOT / 'evidence/quiet-world/browser'
    images = output / 'screenshots'; images.mkdir(parents=True, exist_ok=True)
    report = {'schema':'orbloam-quiet-browser-v2','status':'failed','artifact_sha256':sha256(ARTIFACT),
              'runtime_sha256':sha256(BINARY),'mode':'direct-navigation','errors':[]}
    app = NativeApp(); fault = {}; page = None
    with app, sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox','--disable-dev-shm-usage'])
        report['browser'] = browser.version
        assets = {name:app.expect(200, name).decode() for name in ASSETS}
        report['assets'] = {name:hashlib.sha256(value.encode()).hexdigest() for name,value in assets.items()}
        assert all(value == (ROOT/'web'/name).read_text() for name,value in assets.items()), 'Served code differs from working source'
        def make_page(width=1440,height=960,touch=False,reduced=False):
            context=browser.new_context(viewport={'width':width,'height':height},device_scale_factor=1,has_touch=touch,
                                       reduced_motion='reduce' if reduced else 'no-preference')
            target=context.new_page(); target.on('pageerror',lambda error: report['errors'].append(redact(str(error))))
            if report['mode']=='blank-document-native-http-bridge': bind_bridge(target,app,assets,fault)
            else:
                try:target.goto(app.base,wait_until='domcontentloaded',timeout=15000)
                except Exception as error:
                    report['navigation_error']=redact(str(error)).split('Call log:')[0]
                    if not allow_bridge or 'ERR_BLOCKED_BY_ADMINISTRATOR' not in str(error):raise
                    target.close();target=context.new_page();target.on('pageerror',lambda error: report['errors'].append(redact(str(error))))
                    report['mode']='blank-document-native-http-bridge'
                    report['nonclaims']=['normal browser navigation','CSP/CORS enforcement','TLS','native localStorage permissions/persistence','clipboard permissions','external reverse proxy']
                    bind_bridge(target,app,assets,fault)
            target.wait_for_function('typeof orbloamDiagnostics === "function"',timeout=30000)
            return target
        def entered(p):
            p.wait_for_function("document.querySelector('#auth').classList.contains('hidden')",timeout=30000)
            p.wait_for_function('orbloamDiagnostics().backlogTicks === 0',timeout=30000)
        def owner(state):return next(c for c in state['world']['colonies'] if c['id']==state['me'])
        def wait_idle(p): p.wait_for_function('!orbloamDiagnostics().pendingAction',timeout=30000);p.wait_for_timeout(100)
        def research_click(p,index):
            p.locator('#research-list-toggle').click()
            # All 96 real canvas discoveries also have an accessible button.
            names=app.expect(200,'api/catalog')['research']
            p.get_by_role('button',name=names[index]['name'],exact=False).last.click()
        label_checks = []
        def check_labels(p, stage):
            boxes = p.evaluate('orbloamDiagnostics().researchLabels')
            assert boxes and len(boxes) >= 4, (stage, boxes)
            for i, a in enumerate(boxes):
                for b in boxes[i + 1:]:
                    assert not (a['x'] < b['x'] + b['w'] and a['x'] + a['w'] > b['x'] and
                                a['y'] < b['y'] + b['h'] and a['y'] + a['h'] > b['y']), (stage, a, b)
            label_checks.append({'view': stage, 'visible_labels': len(boxes), 'overlaps': 0})
        try:
            page=make_page();page.screenshot(path=str(images/'welcome.png'))
            page.locator('#nickname').fill('Willowmere');page.locator('#join-form button').click();entered(page)
            page.locator('#dismiss-key').click();page.wait_for_timeout(200)
            assert not page.locator('#sidebar').is_visible() and not page.locator('#selection').is_visible()
            assert not page.locator('#research-detail').is_visible()
            assert page.evaluate("document.documentElement.lang === 'en'")
            assert not page.evaluate("/[\\u3040-\\u30ff\\u3400-\\u9fff]/.test(document.body.innerText)")
            page.screenshot(path=str(images/'world.png'))
            page.locator('#menu-button').click();page.locator('#key-button').click()
            token=page.locator('#key-value').input_value();assert len(token)==64 and page.locator('#key-value').get_attribute('type')=='password'
            page.locator('[data-close="key-dialog"]').click();page.wait_for_function("document.querySelector('#key-value').value === ''")
            # Choose a real canvas root, then traverse its explicit fork.
            page.locator('#open-research').click()
            diag=page.evaluate('orbloamDiagnostics()');node=diag['researchNodes'][0];cam=diag['researchCamera'];width,height=1440,960
            x=width/2+(node['x']-cam['x'])*cam['zoom'];y=(height+90)/2+(node['y']-cam['y'])*cam['zoom']
            page.mouse.click(x,y);page.get_by_role('button',name='Make this discovery',exact=True).click()
            page.wait_for_function("document.querySelector('#research-progress').textContent === '1 / 96'")
            assert owner(app.view(token))['research']['node:0']==1
            page.locator('#research-fit').click();check_labels(page, 'desktop-fit');page.screenshot(path=str(images/'research-tree.png'))
            # The connected root has separate child buttons, not a rank carousel.
            page.mouse.click(x,y)
            assert page.get_by_role('button',name='Kindred sparks ↗',exact=True).is_visible()
            assert page.get_by_role('button',name='A wider circle ↗',exact=True).is_visible()
            page.get_by_role('button',name='A wider circle ↗',exact=True).click()
            assert page.locator('#research-detail h2').inner_text()=='A wider circle'
            check_labels(page, 'desktop-selected-fork');page.screenshot(path=str(images/'research-fork.png'))
            page.locator('#research-close').click()
            # One button places an ordinary, natively paid workshop near the core.
            page.locator('#build-mode').click();page.get_by_role('button',name='Build nearby',exact=True).first.click()
            page.wait_for_function("document.querySelector('#sidebar').classList.contains('hidden')")
            wait_idle(page);state=app.view(token);mine=owner(state);assert len(mine['buildings'])==1
            building=mine['buildings'][0];assert not mine['research'].get('manual:'+str(building['id']))
            page.locator('#build-mode').click();page.locator('.workshop-link').first.click()
            assert page.locator('#selection-body').inner_text().startswith('AN AUTONOMOUS WORKSHOP')
            assert not page.locator('#sidebar').is_visible()
            page.locator('#selection-body summary').click();page.get_by_role('button',name='Use this fixed recipe',exact=True).click();wait_idle(page)
            assert owner(app.view(token))['research']['manual:'+str(building['id'])]==1
            page.get_by_role('button',name='Let residents choose',exact=True).click();wait_idle(page)
            assert owner(app.view(token))['research']['manual:'+str(building['id'])]==0
            page.locator('#close-selection').click()
            # Native action-receipt loss: automatic exact-intent retry, without a manual click.
            if report['mode']=='blank-document-native-http-bridge': fault['drop_action']=True
            before_sequence=owner(app.view(token))['sequence'];page.mouse.click(1050,730,button='right')
            page.wait_for_timeout(2200);wait_idle(page)
            mine=owner(app.view(token));assert mine['sequence']==before_sequence+1
            if report['mode']=='blank-document-native-http-bridge':assert fault.get('dropped_after_commit');report['automatic_lost_reply_retry_exactly_once']=True
            assert mine['to_x']!=mine['from_x'] or mine['to_y']!=mine['from_y']
            # Dragging is navigation, never a move action.
            sequence=mine['sequence'];page.mouse.move(620,450);page.mouse.down();page.mouse.move(790,500,steps=8);page.mouse.up();page.wait_for_timeout(300)
            assert owner(app.view(token))['sequence']==sequence
            page.locator('#center').click();page.wait_for_timeout(7500)  # Let the deliberate fault's transient toast clear.
            # All LOD tiers are exercised through the actual controls.
            views=[]
            for target,name in [(2.7,'close-up'),(.65,'landscape'),(.19,'regional'),(.02,'atlas')]:
                for _ in range(50):
                    z=page.evaluate('orbloamDiagnostics().camera.zoom')
                    if z<=target*1.1 and z>=target/1.4:break
                    page.locator('#zoom-in' if z<target else '#zoom-out').click()
                page.mouse.move(15,300);page.wait_for_timeout(180)
                diag=page.evaluate('orbloamDiagnostics()');views.append(diag)
                page.screenshot(path=str(images/(name+'.png')))
            assert views[-1]['camera']['zoom']>=.02 and views[-1]['rendering']['residents']==0
            assert views[-1]['rendering']['resourceSprites']==0 and views[-1]['rendering']['regionTiles']>0
            assert views[-1]['rendering']['regionalResourceMarks'] > 0
            assert all(math.isfinite(d['rendering']['frameMilliseconds']) for d in views)
            page.mouse.click(930,410);assert page.locator('#selection').is_visible();assert 'region' in page.locator('#selection-body').inner_text().lower()
            page.screenshot(path=str(images/'atlas-inspect.png'));page.locator('#close-selection').click()
            page.keyboard.press('h');assert not page.locator('#toolbar').is_visible();assert page.locator('#restore-ui').is_visible();page.keyboard.press('h')
            # A second client sees untrusted names as text, not executable markup.
            other=make_page();other.locator('#nickname').fill('<script>Birch</script>');other.locator('#join-form button').click();entered(other);other.locator('#dismiss-key').click()
            page.locator('#inventory-button').click();page.locator('[data-tab="neighbors"]').click()
            page.get_by_role('heading',name='<script>Birch</script>',exact=True).wait_for(timeout=15000)
            assert page.locator('#panel-content script').count()==0
            # Mobile recovery, touch navigation, keyboard alternative for small tree nodes.
            mobile=make_page(390,844,touch=True);mobile.locator('#auth summary').click();mobile.locator('#recovery-key').fill(token);mobile.locator('#recover-form button').click();entered(mobile)
            assert mobile.locator('#colony-name').inner_text()=='Willowmere'
            assert mobile.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
            mobile.screenshot(path=str(images/'mobile-world.png'));mobile.locator('#open-research').click();check_labels(mobile, 'mobile-fit');mobile.screenshot(path=str(images/'mobile-tree.png'))
            mobile.locator('#research-list-toggle').click();mobile.get_by_role('button',name='A wider circle',exact=False).click()
            assert mobile.locator('#research-detail').is_visible();mobile.screenshot(path=str(images/'mobile-discovery.png'))
            # Touch pinch using CDP dispatch, no pointerup click side effect.
            mobile.locator('#research-close').click();touch=mobile.context.new_cdp_session(mobile)
            seq=owner(app.view(token))['sequence'];z=mobile.evaluate('orbloamDiagnostics().camera.zoom')
            touch.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':140,'y':370},{'x':250,'y':470}]})
            for i in range(1,6):touch.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':140-i*9,'y':370-i*8},{'x':250+i*9,'y':470+i*8}]})
            touch.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]});mobile.wait_for_timeout(250)
            assert mobile.evaluate('orbloamDiagnostics().camera.zoom')>z
            assert owner(app.view(token))['sequence']==seq
            # Static reduced-motion view must still repaint after a zoom.
            reduced=make_page(1000,700,reduced=True);reduced.locator('#auth summary').click();reduced.locator('#recovery-key').fill(token);reduced.locator('#recover-form button').click();entered(reduced)
            reduced.wait_for_timeout(150);frames=reduced.evaluate('orbloamDiagnostics().frames');reduced.locator('#zoom-out').click();reduced.wait_for_timeout(150);assert reduced.evaluate('orbloamDiagnostics().frames')>frames
            assert all(p.evaluate('orbloamDiagnostics().maximumGameRequests')==1 for p in [page,other,mobile,reduced])
            assert not report['errors'],report['errors']
            report.update(status='passed',observations={'quiet_default':True,'english_interface':True,'native_canvas_research':True,'actual_fork_navigation':True,
                'one_click_paid_building':True,'fixed_and_automatic_modes_persist':True,'drag_does_not_move_core':True,'regional_aggregation_and_detail':True,
                'collision_free_research_labels':label_checks,'four_lod_views':views,'cinematic_mode':True,'hostile_name_rendered_as_text':True,'mobile_no_horizontal_overflow':True,
                'mobile_recovery_same_core':True,'touch_pinch_without_command':True,'reduced_motion_repaints':True,'single_request_lane':True})
        except Exception as error:
            report.update(error=redact(str(error)),traceback=redact(traceback.format_exc()))
            if page:
                try:page.screenshot(path=str(images/'failure.png'))
                except Exception:pass
        finally:browser.close()
    app.verify();report['artifact_unchanged']=sha256(ARTIFACT)==report['artifact_sha256']
    if not report['artifact_unchanged']:report['status']='failed'
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='observations'},indent=2))
    return 0 if report['status']=='passed' else 1

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bridge-if-blocked',action='store_true');args=p.parse_args();raise SystemExit(main(args.bridge_if_blocked))
