// Independent exhaustive integer checks for the render-only aggregation and tree.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import crypto from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {regionBase,nodeAt,lodForZoom,researchOwned,researchReady,LIFE_TICKS} from '../web/world.js';
import {layoutResearch} from '../web/research.js';
const catalog = JSON.parse(execFileSync('python3', ['-c', 'import json; from tools.catalog import CATALOG; print(json.dumps(CATALOG))'], {cwd:fileURLToPath(new URL('..',import.meta.url)),encoding:'utf8'}));
let regions=0;
for(const stride of [1,2,4,8,16,32,64]) for(const [x,y] of [[0,0],[-5,-8],[-16,-16],[7,6],[41,-47],[8000,-7999],[-127,14],[17,128],[777,-777]]) {
  const actual=regionBase(x,y,stride),counts=Array(8).fill(0),capacity=Array(8).fill(0);
  for(let a=x;a<x+stride;a++)for(let b=y;b<y+stride;b++) {const n=nodeAt(a,b);counts[n.kind]++;capacity[n.kind]+=180+n.tier*30;}
  assert.deepEqual(actual.counts,counts);assert.deepEqual(actual.capacity,capacity);regions++;
}
const nodes=layoutResearch(catalog);assert.equal(nodes.length,96);let forks=0;
for(const node of nodes){assert.equal(nodes.filter(n=>n.id===node.id).length,1);const visited=new Set();let current=node;
  while(current.parent>=0){assert.ok(!visited.has(current.id));visited.add(current.id);current=nodes[current.parent];assert.equal(current.branch,node.branch);}
  if(node.children.length>1)forks++;
  assert.equal(researchReady({},node,catalog),node.parent<0);
}
assert.equal(forks,32);let minDistance=Infinity;
for(let a=0;a<nodes.length;a++)for(let b=a+1;b<nodes.length;b++)minDistance=Math.min(minDistance,Math.hypot(nodes[a].x-nodes[b].x,nodes[a].y-nodes[b].y));
assert.ok(minDistance>35,`Minimum separation ${minDistance}`);
const choice={'0':2,'legacy:0':0,'node:0':1,'node:2':1};
assert.equal(researchOwned(choice,catalog.research[1]),false);assert.equal(researchOwned(choice,catalog.research[2]),true);
assert.equal(researchReady(choice,catalog.research[5],catalog),true);assert.equal(researchReady(choice,catalog.research[3],catalog),false);
assert.equal(researchOwned({'0':4},catalog.research[3]),true);
assert.equal(LIFE_TICKS,90);
let transitionSamples=0;
for(let z=.02001;z<4;z+=.001){const a=lodForZoom(z),b=lodForZoom(z+.000001);for(const key of ['resource','detail','people','region']){assert.ok(a[key]>=0&&a[key]<=1);assert.ok(Math.abs(a[key]-b[key])<.001);}assert.ok(a.stride>=1);transitionSamples++;}
const sha=path=>crypto.createHash('sha256').update(fs.readFileSync(new URL(path,import.meta.url))).digest('hex');
const report={schema:'orbloam-presentation-v2',artifact_sha256:sha('../dist/application.lkja'),source_sha256:{world:sha('../web/world.js'),research:sha('../web/research.js'),catalogue:sha('../tools/catalog.py')},status:'passed',regions,terrainCases:63,treeNodes:nodes.length,structuralForks:forks,minimumNodeSeparation:minDistance,continuousLODSamples:transitionSamples,lifetimeSeconds:LIFE_TICKS*10};
fs.mkdirSync(new URL('../evidence/quiet-world/',import.meta.url),{recursive:true});fs.writeFileSync(new URL('../evidence/quiet-world/presentation.json',import.meta.url),JSON.stringify(report,null,2)+'\n');console.log(report);
