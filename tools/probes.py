"""Pure, local-command verification probes. No public HTTP grant or game cheat path."""
from meaning import I, L, F, R, IF, LET
from catalog import ITEMS

COUNTS = [0, 1, 16, 256, 512, 4096]
TICKS = [-1, 0, 1, 359, 360, 375, 720, 1024]


def compose(g):
    a, c = g.a, g.c
    a.list_type('Populations', '@Population')
    a.structure('MachineProbe', {'id': 'i64', 'ready': '@MachineResult', 'blocked': '@MachineResult', 'warehouse': '@MachineResult'})
    a.list_type('MachineProbes', '@MachineProbe')
    a.structure('ProbeReport', {'populations': '@Populations', 'machines': '@MachineProbes', 'before': '@World', 'after': '@World', 'split_equal': 'bool'})

    def select(index, values):
        result = I(values[-1])
        for i in reversed(range(len(values) - 1)):
            result = IF(g.eq(index, I(i)), I(values[i]), result)
        return result

    g.fn('probe-populations', {'i': 'i64', 'out': '@Populations'}, '@Populations', lambda index, out:
         IF(g.less(index, I(len(COUNTS) * len(TICKS))),
            LET([('count', select(g.div(index, I(len(TICKS))), COUNTS)), ('tick', select(g.mod(index, I(len(TICKS))), TICKS)),
                 ('base', c('$new-colony', I(1), I('population probe'), I(0))),
                 ('colony', g.copy('Colony', L('base'), cohorts=g.list('@Cohort', R(first=I(0), count=L('count'), start=I(0)))))],
                c('$probe-populations', g.add(index, I(1)), g.append(out, c('$population', L('colony'), L('tick')), '@Population'))), out))

    inventory = g.map(**{item['key']: 100 for item in ITEMS})
    research = g.map(**{str(branch): 8 for branch in range(8)})
    def machine(index):
        return LET([('rule', c('$recipe-rule', index)),
             ('ctx', R(tick=I(1001), point=R(x=I(0), y=I(0)), radius=I(500), storage=I(1000000), research=research)),
             ('inventory', inventory),
             ('building', R(id=I(1), kind=F(L('rule'), 'kind'), recipe=index, x=I(0), y=I(0), health=I(100),
                progress=g.sub(F(L('rule'), 'period'), I(1)), produced=I(0), enabled=I(True), status=I('working')))],
            R(id=index,
              ready=c('$machine-cycle', L('ctx'), L('inventory'), L('building'), L('rule')),
              blocked=c('$machine-cycle', L('ctx'), g.map(), L('building'), L('rule')),
              warehouse=c('$machine-cycle', L('ctx'), g.mset(L('inventory'), F(L('rule'), 'output'), I(1000000)), L('building'), L('rule'))))
    g.fn('probe-machine', {'index': 'i64'}, '@MachineProbe', machine)
    g.fn('probe-machines', {'i': 'i64', 'out': '@MachineProbes'}, '@MachineProbes', lambda index, out:
         IF(g.less(index, I(72)), c('$probe-machines', g.add(index, I(1)), g.append(out, c('$probe-machine', index), '@MachineProbe')), out))
    g.fn('probe-colony', {'id': 'i64'}, '@Colony', lambda identifier:
         LET([('base', c('$new-colony', identifier, I('oracle colony'), I(1000)))],
             g.copy('Colony', L('base'), inventory=inventory, research=g.map(**{'1': 8, '2': 4, '6': 4, '7': 4}),
                    cohorts=g.list('@Cohort', R(first=I(0), count=I(512), start=I(489))), experience=I(1000))))
    g.fn('probe-world', {}, '@World',
         g.copy('World', c('$empty-world', I(1000)), next_id=I(3), colonies=g.list('@Colony', c('$probe-colony', I(1)), c('$probe-colony', I(2)))))
    g.fn('diagnostics', {}, 'text', LET([('before', c('$probe-world')), ('after', c('$world-step', L('before'))),
                  ('batch', c('$advance-world', L('before'), I(1002), I(2))),
                  ('split', c('$advance-world', L('after'), I(1002), I(1)))],
             c('bytes-to-text', c('json-encode', R(before=L('before'), after=L('after'),
                 populations=c('$probe-populations', I(0), g.list('@Population')),
                 machines=c('$probe-machines', I(0), g.list('@MachineProbe')),
                 split_equal=c('bytes-equal', c('data-encode', L('batch'), types=('@World',)), c('data-encode', L('split'), types=('@World',)))), types=('@ProbeReport',)))))
    a.port('diagnostics', 'diagnostics', target='diagnostics')
