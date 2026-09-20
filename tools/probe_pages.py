"""Bounded public-command result pages, below the runtime's compact-record limit."""
from meaning import I, L, F, R, IF, LET


def compose(g):
    a, c = g.a, g.c
    g.fn('probe-machine-page', {'i': 'i64', 'end': 'i64', 'out': '@MachineProbes'}, '@MachineProbes', lambda index, end, out:
         IF(g.less(index, end), c('$probe-machine-page', g.add(index, I(1)), end,
             g.append(out, c('$probe-machine', index), '@MachineProbe')), out))
    def encode(value, ty):
        return c('bytes-to-text', c('json-encode', value, types=(ty,)))
    world = LET([('before', c('$probe-world')), ('after', c('$world-step', L('before'))),
                 ('batch', c('$advance-world', L('before'), I(1002), I(2))),
                 ('split', c('$advance-world', L('after'), I(1002), I(1)))],
        encode(R(before=L('before'), after=L('after'), populations=g.list('@Population'), machines=g.list('@MachineProbe'),
                 split_equal=c('bytes-equal', c('data-encode', L('batch'), types=('@World',)),
                     c('data-encode', L('split'), types=('@World',)))), '@ProbeReport'))
    g.fn('diagnostic-page', {'page': 'i64'}, 'text', lambda page:
        IF(g.eq(page, I(0)), encode(c('$probe-populations', I(0), g.list('@Population')), '@Populations'),
           IF(g.eq(page, I(1)), world,
              IF(g.both(c('less-equal', I(2), page), g.less(page, I(20))),
                 LET([('start', g.mul(g.sub(page, I(2)), I(4)))],
                     encode(c('$probe-machine-page', L('start'), g.add(L('start'), I(4)), g.list('@MachineProbe')), '@MachineProbes')),
                 I('invalid diagnostic page; expected 0 through 19')))))
    a.port('diagnostic-page', 'diagnostic-page', target='diagnostic-page')
    a.emit('expression.block as=$diagnostics-bounded-output\n  ' + I('Use local command diagnostic-page with one argument 0 through 19. Page 0: lives; page 1: world; pages 2-19: four recipes each.') + '\nexpression.end')
    a.emit('replace.body function=$diagnostics body=$diagnostics-bounded-output')
