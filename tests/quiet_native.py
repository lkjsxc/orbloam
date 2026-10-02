#!/usr/bin/env python3
"""Native forks, overrides, and unchanged typed-save admission across this upgrade."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import time
import traceback
from native import NativeApp, ROOT, ARTIFACT, BINARY, sha256, redact


def owner(state): return next(c for c in state['world']['colonies'] if c['id'] == state['me'])

def rejected(app, token, op, **fields):
    state = app.sync(token); mine = owner(state)
    action = dict(op=op, sequence=mine['sequence']+1, index=0, value=0, x=0, y=0, text=''); action.update(fields)
    status, reply, _ = app.request('api/action', 'POST', action, token)
    assert status == 400 and reply['error'] == 'research_order', (status, reply)
    after = app.view(token); assert owner(after)['sequence'] == mine['sequence'] and owner(after)['essence'] == mine['essence']
    return action


def main(predecessor):
    output = ROOT/'evidence/quiet-world/native.json'
    report = {'schema':'orbloam-quiet-native-v2','status':'failed','artifact_sha256':sha256(ARTIFACT),'runtime_sha256':sha256(BINARY)}
    try:
        app = NativeApp(); token = app.seed(512, 0)
        with app:
            catalog = app.expect(200, 'api/catalog'); assert catalog['version']==2 and catalog['lifespan_ticks']==90
            rejected(app, token, 'research', index=2)  # A child cannot precede its root.
            root, _ = app.action(token,'research',index=0)
            right, intent = app.action(token,'research',index=2)
            mine = owner(right)
            assert mine['research']['0']==2 and mine['research']['legacy:0']==0
            assert mine['research']['node:0']==1 and mine['research']['node:2']==1 and 'node:1' not in mine['research']
            assert sum(c['count'] for c in mine['cohorts'])==608  # Seed 512 + 2 x 48, a disclosed fixture.
            assert app.expect(200,'api/action','POST',intent,token)['world']==right['world']
            rejected(app,token,'research',index=2)  # Duplicate ownership is not a new charge.
            rejected(app,token,'research',index=3)  # Other sibling's child is still unavailable.
            left,_=app.action(token,'research',index=1); assert owner(left)['research']['0']==3
            # Actual user override and automatic mode survive through the native transaction.
            fixed,_=app.action(token,'recipe',index=1,value=0)
            assert owner(fixed)['research']['manual:1']==1
            auto,_=app.action(token,'auto',index=1)
            assert owner(auto)['research']['manual:1']==0
            outsider,_=app.join('Other core'); current=app.sync(outsider); original_buildings=owner(app.view(token))['buildings']
            outsider_action=dict(op='auto',sequence=owner(current)['sequence']+1,index=1,value=0,x=0,y=0,text='')
            status,reply,_=app.request('api/action','POST',outsider_action,outsider)
            assert status==400 and reply['error']=='building_missing'
            assert owner(app.view(token))['buildings']==original_buildings
            saved=app.view(token)
        app.start(); reopened=app.view(token); assert reopened['world']==saved['world'];app.stop();app.verify()
        report['native_journey']={'child_before_root_rejected':True,'right_sibling_before_left_accepted':True,
            'unbought_sibling_remains_unowned':True,'unbought_parent_still_blocks':True,'duplicate_purchase_no_charge':True,
            'replay_same_world':True,'automatic_and_manual_server_modes':True,'foreign_building_override_rejected':True,
            'restart_keeps_branch_ownership':True,'seed_population':512,'population_after_two_fixture_purchases':608}
        if predecessor:
            assert predecessor.is_file()
            report['predecessor_artifact_sha256']=sha256(predecessor)
            old = NativeApp(); shutil.copyfile(predecessor,old.root/'application.lkja')
            key=old.seed(512,0)
            with old:
                before=old.view(key)
                assert 'legacy:1' not in owner(before)['research'] and owner(before)['research']['1']==8
            shutil.copyfile(ARTIFACT,old.root/'application.lkja')
            with old:
                admitted=old.view(key)
                assert admitted['world']==before['world'], 'Viewing old data silently changed it'
                # Existing Reach rank 8 owns nodes 12..19; buy tier 10 directly after its parent (tier 6).
                # Tier 10 costs use the last item of family 1; the seed lacks it. Instead exercise
                # a rank-0 family on old bytes, then check all original rank prefixes survived.
                branch,_=old.action(key,'research',index=0)
                for family,rank in [('1',8),('2',4),('3',8),('4',8),('5',8),('6',4)]:
                    assert owner(branch)['research'][family]==rank
                fixed,_=old.action(key,'recipe',index=1,value=0)
                assert owner(fixed)['research']['manual:1']==1
            old.verify()
            report['old_save_admission']={'exact_world_unchanged_on_view':True,'same_key_accepted':True,'new_discovery_on_old_save':True,
                                         'existing_branch_prefixes_retained':True,'manual_override_on_old_workshop':True,
                                         'schema_rewrite_or_data_reset':False}
        else: report['old_save_admission']='not run: predecessor artifact was not supplied'
        report['status']='passed'
    except Exception as error:report.update(error=redact(str(error)),traceback=redact(traceback.format_exc()))
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    return 0 if report['status']=='passed' else 1

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--predecessor',type=Path);args=p.parse_args();raise SystemExit(main(args.predecessor))
