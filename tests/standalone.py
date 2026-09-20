#!/usr/bin/env python3
"""Verify the offline launch package without project/, web/, tools/, or game helpers."""
from __future__ import annotations
import hashlib
import http.client
import json
from pathlib import Path
import secrets
import shutil
import signal
import socket
import subprocess
import tempfile
import time
import traceback

from native import ROOT, ARTIFACT, BINARY, sha256, redact


def main():
    report={'schema':'orbloam-standalone-v1','status':'failed','artifact_sha256':sha256(ARTIFACT),'runtime_sha256':sha256(BINARY)}
    work=Path(tempfile.mkdtemp(prefix='standalone-',dir=ROOT/'.test-state'))
    package=work/'package with spaces';package.mkdir()
    (package/'runtime').mkdir();(package/'dist').mkdir()
    shutil.copy2(BINARY,package/'runtime/lkjscript')
    shutil.copy2(ROOT/'start.sh',package/'start.sh')
    for name in ['application.lkja','service.deployment.json','SHA256SUMS']:
        shutil.copy2(ROOT/'dist'/name,package/'dist'/name)
    assert not any((package/n).exists() for n in ['project','web','tools','tests'])
    def available_port():
        with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
    def launch(lan=False):
        port=available_port();log=package/'launch.log';handle=log.open('w')
        cmd=['sh',str(package/'start.sh'),'--port',str(port)]+(['--lan'] if lan else [])
        process=subprocess.Popen(cmd,cwd='/tmp',stdout=handle,stderr=subprocess.STDOUT,start_new_session=True)
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            text=log.read_text()
            if any('"event":"ready"' in line.replace(' ','') for line in text.splitlines()):
                return process,handle,port
            if process.poll() is not None:raise AssertionError('Launcher failed: '+redact(text))
            time.sleep(.05)
        process.kill();process.wait();raise TimeoutError('Standalone did not become ready')
    def request(port,path,method='GET',data=None,token=None,host='127.0.0.1'):
        h={};body=None
        if data is not None:h['Content-Type']='application/json';body=json.dumps(data,ensure_ascii=False).encode()
        if token:h['Authorization']='Bearer '+token
        conn=http.client.HTTPConnection(host,port,timeout=20)
        try:
            conn.request(method,path,body,h);res=conn.getresponse();payload=res.read()
            assert res.status in [200,201], (res.status,redact(payload.decode(errors='replace')))
            return json.loads(payload) if 'application/json' in res.getheader('Content-Type','') else payload
        finally:conn.close()
    def stop(process,handle):
        process.send_signal(signal.SIGINT)
        assert process.wait(timeout=35)==0
        handle.close()
        assert not list((package/'dist').glob('.run.*.json'))
    process=None;handle=None
    try:
        process,handle,port=launch()
        assert b'Orbloam' in request(port,'/')
        assert request(port,'/api.js')==(ROOT/'web/api.js').read_bytes()
        token=secrets.token_hex(32)
        registered=request(port,'/api/join','POST',{'name':'Standalone','token':token})
        saved=request(port,'/api/view',token=token)
        process_rows=subprocess.check_output(['ps','-eo','pid=,ppid='],text=True).splitlines()
        children=[row.split()[0] for row in process_rows if len(row.split())==2 and int(row.split()[1])==process.pid]
        executable_paths=[str(Path(f'/proc/{pid}/exe').resolve()) for pid in children]
        assert executable_paths==[str(package/'runtime/lkjscript')],executable_paths
        stop(process,handle);process=None
        process,handle,port=launch(True)
        loaded=request(port,'/api/view',token=token,host='127.0.0.2')
        assert loaded['world']==saved['world'] and loaded['me']==registered['id']
        stop(process,handle);process=None
        verified=subprocess.run([str(package/'runtime/lkjscript'),'data','verify','--root',str(package/'dist/data')],capture_output=True,text=True,timeout=30)
        assert verified.returncode==0
        # Unsafe selection and corrupt data are refused, not repaired by destructive initialization.
        refused=subprocess.run(['sh',str(package/'start.sh'),'--data','../other'],capture_output=True,text=True,timeout=5)
        assert refused.returncode!=0
        corrupt=package/'dist/corrupt-data';shutil.copytree(package/'dist/data',corrupt)
        original_format=(corrupt/'FORMAT').read_bytes()
        (corrupt/'FORMAT').write_bytes(b'not-a-native-data-store\n')
        corrupt_hash=sha256(corrupt/'FORMAT')
        refused=subprocess.run(['sh',str(package/'start.sh'),'--port',str(available_port()),'--data','corrupt-data'],capture_output=True,text=True,timeout=30)
        assert refused.returncode!=0 and sha256(corrupt/'FORMAT')==corrupt_hash
        report.update(status='passed',no_authoring_or_web_checkout=True,only_native_server_child=True,launch_from_unrelated_directory=True,
            paths_with_spaces=True,embedded_assets_equal=True,registration=True,restart_world_equal=True,
            all_ipv4_listener_via_second_loopback=True,data_verified=True,corrupt_store_not_reset=True,parent_traversal_rejected=True,
            ephemeral_descriptors_removed=True,nonclaims=['remote LAN reachability','TLS','old Stillworld data migration'])
    except Exception as error:
        report.update(error=redact(str(error)),traceback=redact(traceback.format_exc()))
    finally:
        if process is not None and process.poll() is None:
            process.send_signal(signal.SIGINT)
            try:process.wait(timeout=35)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        if handle and not handle.closed:handle.close()
    report['artifact_unchanged']=sha256(ARTIFACT)==report['artifact_sha256']
    if not report['artifact_unchanged']:report['status']='failed'
    output=ROOT/'evidence/standalone.json';output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return 0 if report['status']=='passed' else 1


if __name__=='__main__':raise SystemExit(main())
