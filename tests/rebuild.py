#!/usr/bin/env python3
"""One clean accepted-graph check plus equal clean/incremental artifact output."""
from pathlib import Path
import json
import shutil
import subprocess
import tempfile
import time
import traceback
from native import ROOT, BINARY, ARTIFACT, sha256, redact


def main():
    root=ROOT/'.test-state';root.mkdir(exist_ok=True)
    work=Path(tempfile.mkdtemp(prefix='rebuild-',dir=root))
    project=work/'project'
    shutil.copytree(ROOT/'project',project,ignore=shutil.ignore_patterns('derived','LOCK'))
    head=(project/'HEAD').read_bytes()
    report={'schema':'orbloam-accepted-rebuild-v1','artifact_sha256':sha256(ARTIFACT),'runtime_sha256':sha256(BINARY),'status':'failed'}
    def run(name,args):
        began=time.monotonic()
        result=subprocess.run([str(BINARY),'--project',str(project),*args],capture_output=True,text=True,timeout=1200)
        (work/(name+'.txt')).write_text(result.stdout+result.stderr)
        report[name+'_seconds']=time.monotonic()-began
        if result.returncode:raise RuntimeError(redact(result.stdout+result.stderr)[-5000:])
        assert (project/'HEAD').read_bytes()==head, 'A lifecycle command changed accepted authority'
        return result.stdout
    try:
        checked=run('check',['check'])
        assert 'failed=0' in checked and 'differential=equal' in checked
        a=work/'first.lkja';b=work/'second.lkja'
        run('first-build',['build','--output',str(a)])
        run('second-build',['build','--output',str(b)])
        assert sha256(a)==sha256(b)==sha256(ARTIFACT)
        report.update(status='passed',canonical_head_unchanged=True,clean_check_passed=True,
          first_and_second_artifacts_equal=True,shipped_artifact_equal=True)
    except Exception as error:report.update(error=redact(str(error)),traceback=redact(traceback.format_exc()))
    output=ROOT/'evidence/rebuild.json';output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return 0 if report['status']=='passed' else 1


if __name__=='__main__':raise SystemExit(main())
