"""Single chronological world order with bounded catch-up; no discarded time."""
from meaning import I, L, F, R, IF, LET


def compose(g):
    a, c = g.a, g.c
    a.structure('ColonyStep', {'colony': '@Colony', 'nodes': '@Nodes'})
    def evolve(colony, nodes, tick):
        return LET([('population', c('$population', colony, tick)),
                    ('gathered', c('$gather', colony, nodes, L('population'), tick)),
                    ('harvested', g.copy('Colony', colony, inventory=F(L('gathered'), 'inventory'), routes=F(L('gathered'), 'routes'))),
                    ('factories', c('$factories', L('harvested'), L('population'), tick))],
                   R(colony=g.copy('Colony', L('harvested'),
                     inventory=F(L('factories'), 'inventory'), buildings=F(L('factories'), 'buildings'),
                     essence=g.add(F(colony, 'essence'), g.mul(F(L('population'), 'deaths'), g.add(I(6), g.mul(g.rank(colony, 6), I(2))))),
                     deaths=g.add(F(colony, 'deaths'), F(L('population'), 'deaths')),
                     gathered=g.add(F(colony, 'gathered'), F(L('gathered'), 'units')),
                     experience=g.add(F(colony, 'experience'), F(L('gathered'), 'units'), F(L('factories'), 'experience'))),
                     nodes=F(L('gathered'), 'nodes')))
    g.fn('evolve-colony', {'colony': '@Colony', 'nodes': '@Nodes', 'tick': 'i64'}, '@ColonyStep', evolve)

    def neighbor(items, colony, point, tick, index):
        return IF(g.less(index, g.length(items, '@Colony')),
            LET([('other', g.get(items, index, '@Colony')), ('range', g.add(I(300), g.mul(g.rank(colony, 7), I(50))))],
                IF(g.both(c('bool-not', g.eq(F(L('other'), 'id'), F(colony, 'id'))),
                          g.le(F(L('other'), 'created_tick'), tick), g.le(c('$distance', point, c('$position', L('other'), g.mul(tick, I(10000)))), g.mul(L('range'), L('range')))),
                   F(L('other'), 'id'), c('$find-neighbor', items, colony, point, tick, g.add(index, I(1))))), I(0))
    g.fn('find-neighbor', {'items': '@Colonies', 'colony': '@Colony', 'point': '@Point', 'tick': 'i64', 'index': 'i64'}, 'i64', neighbor)
    g.fn('converse', {'colonies': '@Colonies', 'colony': '@Colony', 'tick': 'i64'}, '@Colony', lambda colonies, colony, tick:
         IF(g.eq(g.mod(tick, I(6)), I(0)),
            LET([('neighbor', c('$find-neighbor', colonies, colony, c('$position', colony, g.mul(tick, I(10000))), tick, I(0)))],
                IF(g.less(I(0), L('neighbor')), g.copy('Colony', colony,
                   neighbor=L('neighbor'), conversations=g.add(F(colony, 'conversations'), I(1)),
                   experience=g.add(F(colony, 'experience'), I(2), g.rank(colony, 7)),
                   inventory=g.mset(F(colony, 'inventory'), I('insight'),
                         g.low(c('$storage-limit', colony), g.add(g.mget(F(colony, 'inventory'), I('insight')), I(1))))),
                   g.copy('Colony', colony, neighbor=I(0)))), colony))

    # Rotate admission, but retain canonical colony order in the stored list.
    def world_loop(world, tick, index):
        return IF(g.less(index, g.length(F(world, 'colonies'), '@Colony')),
                  LET([('selected', g.mod(g.add(tick, index), g.length(F(world, 'colonies'), '@Colony'))),
                       ('old', g.get(F(world, 'colonies'), L('selected'), '@Colony')),
                       ('evolved', IF(g.le(F(L('old'), 'created_tick'), tick), c('$evolve-colony', L('old'), F(world, 'nodes'), tick), R(colony=L('old'), nodes=F(world, 'nodes')))),
                       ('colony', IF(g.le(F(L('old'), 'created_tick'), tick), c('$converse', F(world, 'colonies'), F(L('evolved'), 'colony'), tick), L('old'))),
                       ('next', c('$replace-colony', world, L('colony')))],
                      c('$world-step-loop', g.copy('World', L('next'), nodes=F(L('evolved'), 'nodes')), tick, g.add(index, I(1)))),
                  g.copy('World', world, tick=tick))
    g.fn('world-step-loop', {'world': '@World', 'tick': 'i64', 'index': 'i64'}, '@World', world_loop)
    g.fn('world-step', {'world': '@World'}, '@World', lambda world:
         LET([('tick', g.add(F(world, 'tick'), I(1))),
              ('clean', IF(g.eq(g.mod(L('tick'), I(36)), I(0)),
                  g.copy('World', world, nodes=c('$prune-nodes', c('map-entries', F(world, 'nodes'), types=('text', '@Node')),
                                                L('tick'), I(0), '(map text @Node)')), world))],
             c('$world-step-loop', L('clean'), L('tick'), I(0))))
    g.fn('advance-world', {'world': '@World', 'target': 'i64', 'budget': 'i64'}, '@World', lambda world, target, budget:
         IF(g.both(g.less(F(world, 'tick'), target), g.less(I(0), budget)),
            c('$advance-world', c('$world-step', world), target, g.sub(budget, I(1))), world))
    a.test('no-time-reversal', F(c('$advance-world', c('$empty-world', I(100)), I(10), I(12)), 'tick'), I(100))
    a.test('bounded-catchup', F(c('$advance-world', c('$empty-world', I(10)), I(100), I(12)), 'tick'), I(22))
    a.test('exact-catchup', F(c('$advance-world', c('$empty-world', I(10)), I(15), I(12)), 'tick'), I(15))
