#!/usr/bin/env python3
"""Create a self-contained offline ZIP from an already committed, verified checkout.

The Git bundle is embedded too: the playable ZIP retains the accepted source and
history even after a temporary chat link expires. No save/cache/key is included.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT).decode().strip()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    if git('status','--porcelain'):
        raise SystemExit('Commit the accepted source and evidence before packaging; dirty checkout refused.')
    artifact=hashlib.sha256((ROOT/'dist/application.lkja').read_bytes()).hexdigest()
    for name in ['acceptance.json','standalone.json','performance.json','rebuild.json','catalogue.json','browser/report.json']:
        report=json.loads((ROOT/'evidence'/name).read_text())
        if report.get('status')!='passed' or report.get('artifact_sha256')!=artifact:
            raise SystemExit('Missing or mismatched final verification: '+name)
    head=git('rev-parse','main')
    bundle=out/'orbloam-reconstructed.bundle'
    if bundle.exists():raise SystemExit('Bundle output exists; use another output directory.')
    subprocess.run(['git','bundle','create',str(bundle),'main'],cwd=ROOT,check=True)
    subprocess.run(['git','bundle','verify',str(bundle)],cwd=ROOT,check=True)
    source=out/'orbloam-source.zip'
    subprocess.run(['git','archive','--format=zip','--prefix=orbloam/','-o',str(source),'main'],cwd=ROOT,check=True)
    destination=out/'orbloam-offline.zip'
    tracked=git('ls-files','-z').split('\0')
    with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for name in filter(None,tracked):
            path=ROOT/name
            if path.is_symlink():raise SystemExit('Unexpected tracked symlink: '+name)
            archive.write(path,'orbloam/'+name)
        for path in sorted((ROOT/'runtime').iterdir()):
            if not path.is_file() or path.is_symlink():raise SystemExit('Unexpected runtime payload')
            archive.write(path,'orbloam/runtime/'+path.name)
        archive.write(bundle,'orbloam/orbloam-reconstructed.bundle')
        archive.writestr('orbloam/RECOVER-SOURCE.txt',
            'The complete source and accepted graph are present in this ZIP.\n'
            'For Git history, from an unrelated directory use:\n'
            '  git clone --branch main /path/to/orbloam-reconstructed.bundle orbloam-recovered\n'
            'The local main commit is '+head+'.\n'
            'This bundle does not mean remote GitHub main was updated.\n')
    files=[bundle,source,destination]
    (out/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in files))
    print(json.dumps({'local_main':head,'artifact_sha256':artifact,'files':{p.name:p.stat().st_size for p in files}},indent=2))


if __name__=='__main__':main()
