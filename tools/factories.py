"""Workforce-bound processing, finite inventories, location and upkeep."""
from meaning import I, L, F, R, IF, LET


def compose(g):
    a, c = g.a, g.c
    a.structure('FactoryContext', {'tick': 'i64', 'point': '@Point', 'radius': 'i64', 'storage': 'i64', 'research': '@Inventory'})
    a.structure('FactoryState', {'inventory': '@Inventory', 'buildings': '@Buildings', 'workers': 'i64', 'experience': 'i64'})
    a.structure('MachineResult', {'inventory': '@Inventory', 'building': '@Building', 'experience': 'i64'})
    g.fn('pay-item', {'inventory': '@Inventory', 'item': 'text', 'amount': 'i64'}, '@Inventory', lambda inv, item, amount:
         IF(g.less(I(0), amount), c('$item-credit', inv, item, g.sub(I(0), amount)), inv))

    def machine(ctx, inventory, building, rule):
        ready = g.le(F(rule, 'period'), g.add(F(building, 'progress'), I(1)))
        sufficient = g.both(*(g.le(F(rule, 'n' + key), g.mget(inventory, F(rule, key))) for key in ['a', 'b', 'c']))
        free = g.le(g.add(g.mget(inventory, F(rule, 'output')), L('amount')), F(ctx, 'storage'))
        pay = LET([('inv-a', c('$pay-item', inventory, F(rule, 'a'), F(rule, 'na'))),
                   ('inv-b', c('$pay-item', L('inv-a'), F(rule, 'b'), F(rule, 'nb'))),
                   ('inv-c', c('$pay-item', L('inv-b'), F(rule, 'c'), F(rule, 'nc')))],
                  R(inventory=c('$item-credit', L('inv-c'), F(rule, 'output'), L('amount')),
                    building=g.copy('Building', building, progress=I(0), produced=g.add(F(building, 'produced'), L('amount')), status=I('working')),
                    experience=g.mul(F(rule, 'tier'), I(4))))
        blocked = lambda status: R(inventory=inventory, building=g.copy('Building', building, status=I(status)), experience=I(0))
        return LET([('amount', g.mul(F(rule, 'amount'), g.add(I(1),
                   g.div(g.mget(F(ctx, 'research'), g.decimal(F(rule, 'branch'))), I(4)))))],
                   IF(ready, IF(sufficient, IF(free, pay, blocked('warehouse')), blocked('materials')),
                      R(inventory=inventory, building=g.copy('Building', building,
                        progress=g.add(F(building, 'progress'), I(1)), status=I('working')), experience=I(0))))
    g.fn('machine-cycle', {'ctx': '@FactoryContext', 'inventory': '@Inventory', 'building': '@Building', 'rule': '@Recipe'}, '@MachineResult', machine)

    def factory_one(ctx, state, building):
        maintenance = g.eq(g.mod(F(ctx, 'tick'), I(6)), I(0))
        near = g.le(c('$distance', F(ctx, 'point'), R(x=F(building, 'x'), y=F(building, 'y'))), g.mul(F(ctx, 'radius'), F(ctx, 'radius')))
        maintained = g.both(L('near'), g.less(I(0), F(state, 'workers')),
                           g.le(I(1), g.mget(F(state, 'inventory'), I('timber'))), g.le(I(1), g.mget(F(state, 'inventory'), I('stone'))))
        paid = c('$pay-item', c('$pay-item', F(state, 'inventory'), I('timber'), I(1)), I('stone'), I(1))
        health = IF(maintenance, IF(maintained, g.low(I(100), g.add(F(building, 'health'), I(1))),
                                   g.high(I(0), g.sub(F(building, 'health'), I(2)))), F(building, 'health'))
        status = IF(F(building, 'enabled'), IF(L('near'), IF(g.less(I(0), L('health')),
                 IF(g.le(F(L('rule'), 'workers'), F(state, 'workers')), I('working'), I('workers')),
                 I('maintenance')), I('distant')), I('paused'))
        return LET([('rule', c('$recipe-rule', F(building, 'recipe'))), ('near', near), ('health', health),
                    ('inventory', IF(g.both(maintenance, maintained), paid, F(state, 'inventory'))),
                    ('status', status), ('active', g.text_eq(L('status'), I('working'))),
                    ('building', g.copy('Building', building, health=L('health'), status=L('status'))),
                    ('out', IF(L('active'), c('$machine-cycle', ctx, L('inventory'), L('building'), L('rule')),
                               R(inventory=L('inventory'), building=L('building'), experience=I(0))))],
                   R(inventory=F(L('out'), 'inventory'), buildings=g.append(F(state, 'buildings'), F(L('out'), 'building'), '@Building'),
                     workers=IF(L('active'), g.sub(F(state, 'workers'), F(L('rule'), 'workers')), F(state, 'workers')),
                     experience=g.add(F(state, 'experience'), F(L('out'), 'experience'))))
    g.fn('factory-one', {'ctx': '@FactoryContext', 'state': '@FactoryState', 'building': '@Building'}, '@FactoryState', factory_one)
    g.fn('factory-loop', {'ctx': '@FactoryContext', 'buildings': '@Buildings', 'index': 'i64', 'state': '@FactoryState'}, '@FactoryState',
         lambda ctx, buildings, index, state: IF(g.less(index, g.length(buildings, '@Building')),
            c('$factory-loop', ctx, buildings, g.add(index, I(1)), c('$factory-one', ctx, state, g.get(buildings, index, '@Building'))), state))
    g.fn('factories', {'colony': '@Colony', 'population': '@Population', 'tick': 'i64'}, '@FactoryState', lambda colony, population, tick:
         c('$factory-loop', R(tick=tick, point=c('$position', colony, g.mul(tick, I(10000))),
                              radius=g.mul(c('$radius', colony), I(2)), storage=c('$storage-limit', colony), research=F(colony, 'research')),
           F(colony, 'buildings'), I(0), R(inventory=F(colony, 'inventory'), buildings=g.list('@Building'),
           workers=g.add(g.mget(F(population, 'roles'), I('8')), g.mget(F(population, 'roles'), I('9'))), experience=I(0))))
    # These exercise the real rule selector rather than a Python implementation.
    a.test('first-recipe', F(c('$recipe-rule', I(0)), 'output'), I('plank'))
    a.test('last-recipe', F(c('$recipe-rule', I(71)), 'output'), I('world-seed'))
    a.test('last-research', F(c('$research-rule', I(95)), 'tier'), I(12))
