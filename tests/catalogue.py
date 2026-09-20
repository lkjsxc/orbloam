#!/usr/bin/env python3
"""Check dependency reachability of the actual native-served catalogue.

This is a logical content-graph check with an unlimited-resource assumption;
not a claim about balance, production time, or a played-through progression.
"""
import json
from native import NativeApp, ROOT, ARTIFACT, sha256


def main():
    app=NativeApp()
    with app:catalog=app.expect(200,'api/catalog')
    assert len(catalog['recipes'])==72 and len(catalog['research'])==96
    keys=[x['key'] for x in catalog['items']]
    assert len(set(keys))==len(keys)
    outputs={r['output']:r for r in catalog['recipes']}
    assert len(outputs)==72
    graph={r['output']:[r[x] for x in ['a','b','c'] if r['n'+x]>0] for r in catalog['recipes']}
    visited,active=set(catalog['raw'])|{'insight'},set()
    def visit(key):
        if key in visited:return
        assert key in graph and key not in active, ('missing input or cyclic recipe',key)
        active.add(key)
        for predecessor in graph[key]:visit(predecessor)
        active.remove(key);visited.add(key)
    for key in graph:visit(key)
    known=set(catalog['raw'])|{'insight'};ranks=[0]*8;completed=set()
    for _ in range(200):
        before=(len(known),len(completed))
        for recipe in catalog['recipes']:
            facility=catalog['industries'][recipe['kind']]
            assert recipe['rank']>=facility['rank'] and recipe['branch']==facility['branch']
            if ranks[recipe['branch']]>=recipe['rank'] and all(k in known for k in graph[recipe['output']]):known.add(recipe['output'])
        for research in catalog['research']:
            if ranks[research['branch']]+1==research['tier'] and (not research['product_amount'] or research['product'] in known):
                assert research['raw'] in known
                ranks[research['branch']]+=1;completed.add(research['id'])
        if before==(len(known),len(completed)):break
    assert len(completed)==96 and all(rank==12 for rank in ranks) and all(key in known for key in graph)
    report={'schema':'orbloam-catalogue-reachability-v1','status':'passed','artifact_sha256':sha256(ARTIFACT),
            'acyclic_recipes':72,'reachable_research_steps':96,'reachable_products':72,
            'facility_gate_consistent':True,'assumption':'unlimited obtainable inputs and essence; logical unlock graph only',
            'nonclaims':['earned end-to-end progression','economy balance','time to completion']}
    (ROOT/'evidence/catalogue.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    app.verify()


if __name__=='__main__':main()
