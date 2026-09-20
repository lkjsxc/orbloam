#!/usr/bin/env python3
"""Bounded live native HTTP capacity observation, not an old-engine speedup ratio."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import platform
import statistics
import time
import traceback

from native import NativeApp, ROOT, ARTIFACT, BINARY, sha256, redact


def resource(pid):
    stat = Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
    cpu = (int(stat[11])+int(stat[12])) / os.sysconf('SC_CLK_TCK')
    status = Path(f'/proc/{pid}/status').read_text().splitlines()
    rss = int(next(line.split()[1] for line in status if line.startswith('VmRSS:'))) * 1024
    return cpu, rss


def percentile(values, q):
    ordered=sorted(values)
    return ordered[min(len(ordered)-1, max(0, int(len(ordered)*q)-1))]


def measure(population, duration):
    report={'schema':'orbloam-live-capacity-v1','artifact_sha256':sha256(ARTIFACT),'runtime_sha256':sha256(BINARY),
       'status':'failed','fixture_population':population,'fixture_workshops':8,'requested_wall_seconds':duration,
       'operating_system':platform.platform(),'cpu_affinity_count':len(os.sched_getaffinity(0)),
       'cpu_model': next((s.split(':',1)[1].strip() for s in Path('/proc/cpuinfo').read_text().splitlines() if s.startswith('model name')),'unknown'),
       'nonclaims':['unchanged-workload speedup versus Stillworld','many busy colonies','indefinite real time','every CPU','browser frame rate']}
    for name in ['cpu.max','memory.max']:
        path=Path('/sys/fs/cgroup')/name
        if path.exists():report[name]=path.read_text().strip()
    app=NativeApp()
    token=app.seed(population,0)
    samples=[]
    with app:
        state=app.sync(token)
        initial=next(c for c in state['world']['colonies'] if c['id']==state['me'])
        start=time.monotonic()
        cpu_start,peak=resource(app.process.pid)
        next_request=start
        while time.monotonic()-start<duration:
            if time.monotonic()<next_request:time.sleep(next_request-time.monotonic())
            before=time.monotonic()
            status,state,_=app.request('api/sync','POST',{},token)
            if status!=200:raise AssertionError('Native live sync failed: '+redact(str(state)))
            cpu,rss=resource(app.process.pid);peak=max(peak,rss)
            samples.append({'wall_seconds':time.monotonic()-start,'latency_seconds':time.monotonic()-before,
                'backlog_ticks':state['backlog_ticks'],'world_tick':state['world']['tick'],'rss_bytes':rss,'cpu_seconds':cpu-cpu_start})
            next_request=max(time.monotonic(),next_request+1.0)
        elapsed=time.monotonic()-start
        cpu_end,_=resource(app.process.pid)
        before=time.monotonic()
        moved,intent=app.action(token,'move',x=-170,y=18)
        action_elapsed=time.monotonic()-before
        confirmed=next(c for c in moved['world']['colonies'] if c['id']==moved['me'])
        assert confirmed['to_x']==-170 and confirmed['to_y']==18
        assert app.expect(200,'api/action','POST',intent,token)['world']==moved['world']
        final=next(c for c in state['world']['colonies'] if c['id']==state['me'])
        assert final['gathered']>initial['gathered']
        assert all(b['produced']>0 for b in final['buildings'])
        assert state['backlog_ticks']==0
        report.update(status='passed',measured_wall_seconds=elapsed,requests=len(samples),
            final_backlog_ticks=state['backlog_ticks'],maximum_sampled_backlog_ticks=max(s['backlog_ticks'] for s in samples),
            median_sync_seconds=statistics.median(s['latency_seconds'] for s in samples),
            p95_sync_seconds=percentile([s['latency_seconds'] for s in samples],.95),
            maximum_sync_seconds=max(s['latency_seconds'] for s in samples),
            cpu_seconds=cpu_end-cpu_start,peak_sampled_rss_bytes=peak,post_load_move_seconds=action_elapsed,
            actual_gathered_units=final['gathered']-initial['gathered'],workshop_products=[b['produced'] for b in final['buildings']],
            post_load_replay_equal=True,samples=samples)
    app.verify()
    report['data_verified_after_shutdown']=True
    report['artifact_unchanged']=sha256(ARTIFACT)==report['artifact_sha256']
    if not report['artifact_unchanged']:report['status']='failed'
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--population',type=int,default=512)
    parser.add_argument('--seconds',type=float,default=120)
    parser.add_argument('--output',type=Path,default=ROOT/'evidence/performance.json')
    args=parser.parse_args()
    if not 1<=args.population<=4096 or not 30<=args.seconds<=1800:parser.error('population 1..4096, seconds 30..1800')
    try:report=measure(args.population,args.seconds)
    except Exception as error:report={'status':'failed','error':redact(str(error)),'traceback':redact(traceback.format_exc()),'artifact_sha256':sha256(ARTIFACT)}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='samples'},indent=2))
    raise SystemExit(0 if report['status']=='passed' else 1)
