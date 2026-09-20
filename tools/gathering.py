"""Procedural shared deposits; exact per-role demand and chronological allocation."""
from meaning import I, L, F, R, IF, LET
from catalog import RAW


def compose(g):
    a, c = g.a, g.c
    a.structure('Candidate', {'key': 'text', 'node': '@Node', 'distance': 'i64', 'valid': 'bool'})
    a.structure('GatherContext', {'point': '@Point', 'tick': 'i64', 'roles': '@Inventory', 'tier': 'i64',
                                  'radius': 'i64', 'multiplier': 'i64', 'storage': 'i64',
                                  'min_x': 'i64', 'max_x': 'i64', 'min_y': 'i64', 'max_y': 'i64'})
    a.structure('GatherState', {'inventory': '@Inventory', 'nodes': '@Nodes', 'routes': '@Routes', 'units': 'i64'})
    g.fn('node-capacity', {'node': '@Node'}, 'i64', lambda n: g.add(I(180), g.mul(I(30), F(n, 'tier'))))
    g.fn('node-regrowth', {'node': '@Node'}, 'i64', lambda n: g.add(I(2), g.div(F(n, 'tier'), I(3))))
    g.fn('node-key', {'cx': 'i64', 'cy': 'i64'}, 'text', lambda x, y: g.concat(g.concat(g.decimal(x), I(':')), g.decimal(y)))
    def generated(cx, cy, tick):
        return LET([('salt', g.mod(g.add(g.mul(cx, I(92821)), g.mul(cy, I(68917)), I(19139)), I(2147483647))),
                    ('tier', g.add(I(1), g.div(g.high(c('$abs', cx), c('$abs', cy)), I(8))))],
                   R(stock=g.add(I(180), g.mul(I(30), L('tier'))), tick=tick,
                     x=g.add(g.mul(cx, I(128)), I(24), g.mod(L('salt'), I(80))),
                     y=g.add(g.mul(cy, I(128)), I(24), g.mod(g.div(L('salt'), I(97)), I(80))),
                     kind=g.mod(g.add(cx, g.mul(cy, I(3))), I(8)), tier=L('tier')))
    g.fn('generated-node', {'cx': 'i64', 'cy': 'i64', 'tick': 'i64'}, '@Node', generated)
    g.fn('available-node', {'node': '@Node', 'tick': 'i64'}, 'i64', lambda n, t:
         g.low(c('$node-capacity', n), g.add(F(n, 'stock'), g.mul(g.high(I(0), g.sub(t, F(n, 'tick'))), c('$node-regrowth', n)))))
    # Enumerate only cells of the required resource kind. Each row advances by eight
    # columns, rather than rescanning every cell for every role. Bounds cover the FULL
    # research radius; exact squared-distance, depletion and tracking checks still apply.
    def consider(ctx, nodes, cx, cy, best, allow_new):
        return LET([('node', c('$generated-node', cx, cy, F(ctx, 'tick'))),
                    ('distance', c('$distance', F(ctx, 'point'), R(x=F(L('node'), 'x'), y=F(L('node'), 'y'))))],
            IF(g.both(g.le(F(L('node'), 'tier'), F(ctx, 'tier')),
                      g.le(L('distance'), g.mul(F(ctx, 'radius'), F(ctx, 'radius'))),
                      g.less(L('distance'), F(best, 'distance'))),
                LET([('key', c('$node-key', cx, cy)),
                     ('stored', g.mget(nodes, L('key'), g.copy('Node', L('node'), tick=I(-1)), '@Node')),
                     ('actual', IF(g.less(F(L('stored'), 'tick'), I(0)), L('node'), L('stored')))],
                    IF(g.both(g.either(allow_new, g.le(I(0), F(L('stored'), 'tick'))),
                              g.less(I(0), c('$available-node', L('actual'), F(ctx, 'tick')))),
                       R(key=L('key'), node=L('actual'), distance=L('distance'), valid=I(True)), best)), best))
    g.fn('consider-node', {'ctx': '@GatherContext', 'nodes': '@Nodes', 'cx': 'i64', 'cy': 'i64', 'best': '@Candidate', 'allow-new': 'bool'}, '@Candidate', consider)
    g.fn('find-node-columns', {'ctx': '@GatherContext', 'nodes': '@Nodes', 'cx': 'i64', 'cy': 'i64', 'best': '@Candidate', 'allow-new': 'bool'}, '@Candidate',
         lambda ctx, nodes, cx, cy, best, allow: IF(g.le(cx, F(ctx, 'max_x')),
             c('$find-node-columns', ctx, nodes, g.add(cx, I(8)), cy, c('$consider-node', ctx, nodes, cx, cy, best, allow), allow), best))
    g.fn('find-node-rows', {'ctx': '@GatherContext', 'nodes': '@Nodes', 'job': 'i64', 'cy': 'i64', 'best': '@Candidate', 'allow-new': 'bool'}, '@Candidate',
         lambda ctx, nodes, job, cy, best, allow: IF(g.le(cy, F(ctx, 'max_y')),
             LET([('cx', g.add(F(ctx, 'min_x'), g.mod(g.sub(g.sub(job, g.mul(cy, I(3))), F(ctx, 'min_x')), I(8)))),
                  ('next', c('$find-node-columns', ctx, nodes, L('cx'), cy, best, allow))],
                 c('$find-node-rows', ctx, nodes, job, g.add(cy, I(1)), L('next'), allow)), best))
    empty = R(stock=I(0), tick=I(0), x=I(0), y=I(0), kind=I(0), tier=I(0))
    g.fn('find-node', {'ctx': '@GatherContext', 'nodes': '@Nodes', 'job': 'i64'}, '@Candidate', lambda ctx, nodes, job:
         c('$find-node-rows', ctx, nodes, job, F(ctx, 'min_y'), R(key=I(''), node=empty, distance=I(9000000000000000), valid=I(False)),
           g.less(c('map-length', nodes, types=('text', '@Node')), I(4096))))
    result = I(RAW[-1])
    for i in reversed(range(7)):
        result = IF(g.eq(L('$raw-item-job'), I(i)), I(RAW[i]), result)
    g.fn('raw-item', {'job': 'i64'}, 'text', result)

    def extract(ctx, state, job, candidate):
        return LET([
            ('item', c('$raw-item', job)), ('key', F(candidate, 'key')),
            ('stored', g.mget(F(state, 'nodes'), L('key'), g.copy('Node', F(candidate, 'node'), tick=I(-1)), '@Node')),
            ('node', IF(g.less(F(L('stored'), 'tick'), I(0)), F(candidate, 'node'), L('stored'))),
            ('workers', g.mget(F(ctx, 'roles'), g.decimal(job))),
            ('available', c('$available-node', L('node'), F(ctx, 'tick'))),
            ('wanted', g.mul(g.add(I(1), g.mul(L('workers'), F(ctx, 'multiplier'))), F(L('node'), 'tier'))),
            ('can-track', g.either(g.le(I(0), F(L('stored'), 'tick')), g.less(c('map-length', F(state, 'nodes'), types=('text', '@Node')), I(4096)))),
            ('take', IF(L('can-track'), g.high(I(0), g.low(L('available'), g.low(L('wanted'),
                         g.sub(F(ctx, 'storage'), g.mget(F(state, 'inventory'), L('item')))))), I(0)))],
            R(inventory=c('$item-credit', F(state, 'inventory'), L('item'), L('take')),
              nodes=IF(g.less(I(0), L('take')), g.mset(F(state, 'nodes'), L('key'),
                       g.copy('Node', L('node'), tick=F(ctx, 'tick'), stock=g.sub(L('available'), L('take'))), '@Node'), F(state, 'nodes')),
              routes=g.append(F(state, 'routes'), R(job=job, x=F(L('node'), 'x'), y=F(L('node'), 'y'), tier=F(L('node'), 'tier'),
                                                    units=L('take'), workers=L('workers')), '@Route'),
              units=g.add(F(state, 'units'), L('take'))))
    g.fn('extract-node', {'ctx': '@GatherContext', 'state': '@GatherState', 'job': 'i64', 'candidate': '@Candidate'}, '@GatherState', extract)
    g.fn('gather-loop', {'ctx': '@GatherContext', 'state': '@GatherState', 'job': 'i64'}, '@GatherState', lambda ctx, state, job:
         IF(g.less(job, I(8)), LET([('candidate', c('$find-node', ctx, F(state, 'nodes'), job)),
            ('next', IF(F(L('candidate'), 'valid'), c('$extract-node', ctx, state, job, L('candidate')), state))],
              c('$gather-loop', ctx, L('next'), g.add(job, I(1)))), state))
    def gather(colony, nodes, population, tick):
        return LET([('point', c('$position', colony, g.mul(tick, I(10000)))), ('radius', c('$radius', colony))],
            c('$gather-loop',
              R(point=L('point'), tick=tick, roles=F(population, 'roles'),
                tier=g.add(I(1), g.mul(g.rank(colony, 1), I(2)), g.div(c('$level', colony), I(25))),
                radius=L('radius'), multiplier=g.add(I(1), g.rank(colony, 2)), storage=c('$storage-limit', colony),
                min_x=c('$floor-cell', g.sub(F(L('point'), 'x'), L('radius'))), max_x=c('$floor-cell', g.add(F(L('point'), 'x'), L('radius'))),
                min_y=c('$floor-cell', g.sub(F(L('point'), 'y'), L('radius'))), max_y=c('$floor-cell', g.add(F(L('point'), 'y'), L('radius')))),
              R(inventory=F(colony, 'inventory'), nodes=nodes, routes=g.list('@Route'), units=I(0)), I(0)))
    g.fn('gather', {'colony': '@Colony', 'nodes': '@Nodes', 'population': '@Population', 'tick': 'i64'}, '@GatherState', gather)
    a.structure('NodeEntry', {'key': 'text', 'value': '@Node'})
    a.list_type('NodeEntries', '@NodeEntry')
    # Empty/full deposits have no history-dependent state; only those can be omitted.
    g.fn('prune-nodes', {'items': '@NodeEntries', 'tick': 'i64', 'index': 'i64', 'out': '@Nodes'}, '@Nodes',
         lambda items, tick, index, out: IF(g.less(index, g.length(items, '@NodeEntry')),
            LET([('entry', g.get(items, index, '@NodeEntry')), ('node', F(L('entry'), 'value'))],
                c('$prune-nodes', items, tick, g.add(index, I(1)),
                  IF(g.less(c('$available-node', L('node'), tick), c('$node-capacity', L('node'))),
                     g.mset(out, F(L('entry'), 'key'), L('node'), '@Node'), out))), out))
    a.test('negative-grid', c('$floor-cell', I(-1)), I(-1))
    a.test('negative-modulus', c('$mod', I(-9), I(8)), I(7))
    a.test('deposit-capacity', c('$node-capacity', c('$generated-node', I(0), I(0), I(0))), I(210))
    a.test('distant-resource-tier', F(c('$generated-node', I(80), I(-16), I(0)), 'tier'), I(11))
    a.test('finite-regrowth', c('$available-node', g.copy('Node', c('$generated-node', I(0), I(0), I(0)), stock=I(1)), I(9999)), I(210))
