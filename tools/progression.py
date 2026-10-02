"""Branching prerequisite ownership, preserving old ranks without rewriting saves."""
from meaning import I, L, F, IF, LET
from catalog import PARENTS


def compose(g):
    c = g.c
    def parent(index):
        local = g.mod(index, I(12))
        out = I(PARENTS[-1])
        for n in reversed(range(11)):
            out = IF(g.eq(local, I(n)), I(PARENTS[n]), out)
        return LET([('parent', out)], IF(g.less(L('parent'), I(0)), I(-1),
               g.add(g.mul(g.div(index, I(12)), I(12)), L('parent'))))
    g.fn('research-parent', {'index': 'i64'}, 'i64', parent)
    # Once a family is first edited, its old rank is frozen as a legacy prefix.
    # A new discovery gets an independent ID. Branch rank continues to count
    # acquired discoveries for capacities, yields and recipe access.
    g.fn('research-owned', {'research': '@Inventory', 'index': 'i64'}, 'bool', lambda research, index:
         LET([('family', g.decimal(g.div(index, I(12)))),
              ('legacy', g.mget(research, g.concat(I('legacy:'), L('family')), g.mget(research, L('family'))))],
             g.either(g.less(g.mod(index, I(12)), L('legacy')),
                      g.eq(g.mget(research, g.concat(I('node:'), g.decimal(index))), I(1)))))
    g.fn('research-ready', {'research': '@Inventory', 'index': 'i64'}, 'bool', lambda research, index:
         g.both(g.le(I(0), index), g.less(index, I(96)),
           c('bool-not', c('$research-owned', research, index)),
           LET([('parent', c('$research-parent', index))],
               IF(g.less(L('parent'), I(0)), I(True), c('$research-owned', research, L('parent'))))))
    g.fn('research-credit', {'research': '@Inventory', 'index': 'i64'}, '@Inventory', lambda research, index:
         LET([('family', g.decimal(g.div(index, I(12)))), ('rank', g.mget(research, L('family'))),
              ('key', g.concat(I('legacy:'), L('family'))),
              ('retained', g.mset(research, L('key'), g.mget(research, L('key'), L('rank')))),
              ('acquired', g.mset(L('retained'), g.concat(I('node:'), g.decimal(index)), I(1)))],
             g.mset(L('acquired'), L('family'), g.add(L('rank'), I(1)))))
    initial = g.map()
    root = c('$research-credit', initial, I(0))
    right = c('$research-credit', root, I(2))
    legacy = g.map(**{'0': 4})
    cases = [
        ('root-ready', c('$research-ready', initial, I(0)), True),
        ('parent-required', c('$research-ready', initial, I(2)), False),
        ('left-fork-ready', c('$research-ready', root, I(1)), True),
        ('right-fork-ready', c('$research-ready', root, I(2)), True),
        ('sibling-not-auto-owned', c('$research-owned', right, I(1)), False),
        ('right-leaf-ready', c('$research-ready', right, I(5)), True),
        ('left-leaf-still-locked', c('$research-ready', right, I(3)), False),
        ('duplicate-research-blocked', c('$research-ready', right, I(2)), False),
        ('legacy-retained', c('$research-owned', legacy, I(3)), True),
        ('legacy-branch-choice', c('$research-ready', legacy, I(6)), True),
        ('legacy-not-inflated', c('$research-owned', c('$research-credit', legacy, I(6)), I(4)), False),
    ]
    for name, actual, expected in cases:
        g.a.test('branch-' + name, actual, I(expected))
