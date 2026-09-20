"""Pure validated commands. Authentication, sequencing and commit live in service.py."""
from meaning import I, L, F, R, IF, LET


def compose(g):
    a, c = g.a, g.c
    a.structure('Action', {'op': 'text', 'sequence': 'i64', 'index': 'i64', 'value': 'i64', 'x': 'i64', 'y': 'i64', 'text': 'text'})
    a.structure('ActionResult', {'world': '@World', 'ok': 'bool', 'error': 'text'})
    g.fn('find-colony-index', {'colonies': '@Colonies', 'id': 'i64', 'index': 'i64'}, 'i64', lambda items, identifier, index:
         IF(g.less(index, g.length(items, '@Colony')), IF(g.eq(F(g.get(items, index, '@Colony'), 'id'), identifier), index,
            c('$find-colony-index', items, identifier, g.add(index, I(1)))), I(-1)))
    g.fn('find-building-index', {'buildings': '@Buildings', 'id': 'i64', 'index': 'i64'}, 'i64', lambda items, identifier, index:
         IF(g.less(index, g.length(items, '@Building')), IF(g.eq(F(g.get(items, index, '@Building'), 'id'), identifier), index,
            c('$find-building-index', items, identifier, g.add(index, I(1)))), I(-1)))
    g.fn('building-spacing', {'buildings': '@Buildings', 'point': '@Point', 'index': 'i64'}, 'bool', lambda items, point, index:
         IF(g.less(index, g.length(items, '@Building')), LET([('building', g.get(items, index, '@Building'))],
            IF(g.less(c('$distance', point, R(x=F(L('building'), 'x'), y=F(L('building'), 'y'))), I(576)), I(False),
               c('$building-spacing', items, point, g.add(index, I(1))))), I(True)))
    g.fn('action-bounds', {'action': '@Action'}, 'bool', lambda action: g.both(
        g.le(I(1), F(action, 'sequence')), g.le(F(action, 'sequence'), I(1000000000000)),
        g.le(I(0), F(action, 'index')), g.le(F(action, 'index'), I(1000000)),
        g.le(I(0), F(action, 'value')), g.le(F(action, 'value'), I(1000000000)),
        g.le(I(-1000000), F(action, 'x')), g.le(F(action, 'x'), I(1000000)),
        g.le(I(-1000000), F(action, 'y')), g.le(F(action, 'y'), I(1000000)),
        g.le(c('text-length', F(action, 'text')), I(64)), g.le(c('text-length', F(action, 'op')), I(16))))
    def fail(world, code):
        return R(world=world, ok=I(False), error=I(code))
    def success(world, colony):
        return R(world=c('$replace-colony', world, colony), ok=I(True), error=I(''))
    g.fail, g.success = fail, success

    def move(world, colony, action, now):
        return LET([('point', c('$position', colony, now)),
                    ('dx', c('$abs', g.sub(F(action, 'x'), F(L('point'), 'x')))),
                    ('dy', c('$abs', g.sub(F(action, 'y'), F(L('point'), 'y')))),
                    ('distance', g.add(g.high(L('dx'), L('dy')), g.div(g.low(L('dx'), L('dy')), I(2)))),
                    ('speed', g.add(I(24), g.mul(g.rank(colony, 1), I(2))))],
                   success(world, g.copy('Colony', colony, from_x=F(L('point'), 'x'), from_y=F(L('point'), 'y'),
                     to_x=F(action, 'x'), to_y=F(action, 'y'), move_at=now,
                     move_ms=g.high(I(1), g.div(g.add(g.mul(L('distance'), I(1000)), g.sub(L('speed'), I(1))), L('speed'))))))
    g.fn('action-move', {'world': '@World', 'colony': '@Colony', 'action': '@Action', 'now': 'i64'}, '@ActionResult', move)

    def research(world, colony, action):
        return LET([('rule', c('$research-rule', F(action, 'index'))),
                    ('rank', g.rank(colony, F(L('rule'), 'branch')))],
             IF(g.eq(g.add(L('rank'), I(1)), F(L('rule'), 'tier')),
                IF(g.both(g.le(F(L('rule'), 'essence'), F(colony, 'essence')),
                          g.le(F(L('rule'), 'raw_amount'), g.mget(F(colony, 'inventory'), F(L('rule'), 'raw'))),
                          g.le(F(L('rule'), 'product_amount'), g.mget(F(colony, 'inventory'), F(L('rule'), 'product')))),
                   LET([('raw-paid', c('$pay-item', F(colony, 'inventory'), F(L('rule'), 'raw'), F(L('rule'), 'raw_amount'))),
                        ('paid', c('$pay-item', L('raw-paid'), F(L('rule'), 'product'), F(L('rule'), 'product_amount')))],
                       success(world, g.copy('Colony', colony, inventory=L('paid'),
                           research=g.mset(F(colony, 'research'), g.decimal(F(L('rule'), 'branch')), F(L('rule'), 'tier')),
                           essence=g.sub(F(colony, 'essence'), F(L('rule'), 'essence')),
                           experience=g.add(F(colony, 'experience'), g.mul(F(L('rule'), 'tier'), I(20))),
                           cohorts=IF(g.eq(F(L('rule'), 'branch'), I(0)),
                               g.append(F(colony, 'cohorts'), R(first=F(c('$population', colony, F(world, 'tick')), 'capacity'),
                                    count=I(48), start=g.add(F(world, 'tick'), I(1))), '@Cohort'), F(colony, 'cohorts'))))),
                   fail(world, 'research_cost')), fail(world, 'research_order')))
    g.fn('action-research', {'world': '@World', 'colony': '@Colony', 'action': '@Action'}, '@ActionResult', research)

    def build(world, colony, action, now):
        return LET([('rule', c('$recipe-rule', F(action, 'value'))),
                    ('timber', g.add(I(30), g.mul(F(action, 'index'), I(8)))),
                    ('stone', g.add(I(20), g.mul(F(action, 'index'), I(5)))),
                    ('point', R(x=F(action, 'x'), y=F(action, 'y'))),
                    ('capacity', g.low(I(64), g.add(I(4), g.mul(g.rank(colony, 3), I(4)), g.div(c('$level', colony), I(10)))))],
            IF(g.both(g.eq(F(action, 'index'), F(L('rule'), 'kind')), g.le(F(L('rule'), 'rank'), g.rank(colony, F(L('rule'), 'branch')))),
              IF(g.less(g.length(F(colony, 'buildings'), '@Building'), L('capacity')),
                IF(g.le(c('$distance', L('point'), c('$position', colony, now)), g.mul(c('$radius', colony), c('$radius', colony))),
                  IF(c('$building-spacing', F(colony, 'buildings'), L('point'), I(0)),
                    IF(g.both(g.le(L('timber'), g.inv(colony, 'timber')), g.le(L('stone'), g.inv(colony, 'stone'))),
                      LET([('paid', c('$pay-item', c('$pay-item', F(colony, 'inventory'), I('timber'), L('timber')), I('stone'), L('stone'))),
                           ('building', R(id=F(colony, 'next_building'), kind=F(action, 'index'), recipe=F(action, 'value'),
                              x=F(action, 'x'), y=F(action, 'y'), health=I(100), progress=I(0), produced=I(0), enabled=I(True), status=I('workers')))],
                          success(world, g.copy('Colony', colony, inventory=L('paid'),
                            buildings=g.append(F(colony, 'buildings'), L('building'), '@Building'),
                            next_building=g.add(F(colony, 'next_building'), I(1)), experience=g.add(F(colony, 'experience'), I(15))))),
                      fail(world, 'building_cost')), fail(world, 'building_spacing')), fail(world, 'out_of_range')),
                fail(world, 'building_limit')), fail(world, 'recipe_locked')))
    g.fn('action-build', {'world': '@World', 'colony': '@Colony', 'action': '@Action', 'now': 'i64'}, '@ActionResult', build)

    g.fn('edit-buildings-loop', {'items': '@Buildings', 'building': '@Building', 'remove': 'bool', 'i': 'i64', 'out': '@Buildings'}, '@Buildings',
         lambda items, building, remove, i, out: IF(g.less(i, g.length(items, '@Building')),
             LET([('old', g.get(items, i, '@Building')), ('same', g.eq(F(L('old'), 'id'), F(building, 'id')))],
                 c('$edit-buildings-loop', items, building, remove, g.add(i, I(1)),
                   IF(g.both(L('same'), remove), out, g.append(out, IF(L('same'), building, L('old')), '@Building')))), out))
    def edited(world, colony, building, inventory, remove=I(False)):
        return success(world, g.copy('Colony', colony, inventory=inventory, buildings=c('$edit-buildings-loop',
            F(colony, 'buildings'), building, remove, I(0), g.list('@Building'))))
    def building_action(world, colony, action, building):
        recipe = LET([('rule', c('$recipe-rule', F(action, 'value')))],
            IF(g.both(g.eq(F(L('rule'), 'kind'), F(building, 'kind')), g.le(F(L('rule'), 'rank'), g.rank(colony, F(L('rule'), 'branch')))),
               edited(world, colony, g.copy('Building', building, recipe=F(action, 'value'), progress=I(0), status=I('workers')), F(colony, 'inventory')),
               fail(world, 'recipe_locked')))
        repair = IF(g.both(g.le(I(5), g.inv(colony, 'timber')), g.le(I(5), g.inv(colony, 'stone'))),
             edited(world, colony, g.copy('Building', building, health=I(100)),
                c('$pay-item', c('$pay-item', F(colony, 'inventory'), I('timber'), I(5)), I('stone'), I(5))), fail(world, 'building_cost'))
        demolish = LET([('wood', g.div(g.add(I(30), g.mul(F(building, 'kind'), I(8))), I(4))),
                        ('stone', g.div(g.add(I(20), g.mul(F(building, 'kind'), I(5))), I(4)))],
            IF(g.both(g.le(g.add(g.inv(colony, 'timber'), L('wood')), c('$storage-limit', colony)),
                      g.le(g.add(g.inv(colony, 'stone'), L('stone')), c('$storage-limit', colony))),
               edited(world, colony, building, c('$item-credit', c('$item-credit', F(colony, 'inventory'), I('timber'), L('wood')), I('stone'), L('stone')), I(True)),
               fail(world, 'warehouse_full')))
        return IF(g.text_eq(F(action, 'op'), I('recipe')), IF(g.less(F(action, 'value'), I(72)), recipe, fail(world, 'invalid_action')),
             IF(g.text_eq(F(action, 'op'), I('pause')), IF(g.le(F(action, 'value'), I(1)),
                edited(world, colony, g.copy('Building', building, enabled=g.eq(F(action, 'value'), I(1))), F(colony, 'inventory')), fail(world, 'invalid_action')),
             IF(g.text_eq(F(action, 'op'), I('repair')), repair, demolish)))
    g.fn('action-building', {'world': '@World', 'colony': '@Colony', 'action': '@Action', 'building': '@Building'}, '@ActionResult', building_action)
    g.fn('action-edit-building', {'world': '@World', 'colony': '@Colony', 'action': '@Action'}, '@ActionResult', lambda world, colony, action:
         LET([('index', c('$find-building-index', F(colony, 'buildings'), F(action, 'index'), I(0)))],
             IF(g.le(I(0), L('index')), c('$action-building', world, colony, action, g.get(F(colony, 'buildings'), L('index'), '@Building')),
                fail(world, 'building_missing'))))

    def transfer(world, colony, action, now):
        return LET([('index', c('$find-colony-index', F(world, 'colonies'), F(action, 'index'), I(0)))],
            IF(g.both(g.le(I(0), L('index')), c('bool-not', g.eq(F(action, 'index'), F(colony, 'id'))), g.less(I(0), F(action, 'value'))),
              LET([('other', g.get(F(world, 'colonies'), L('index'), '@Colony')), ('range', g.add(I(500), g.mul(g.rank(colony, 7), I(100))))],
                IF(g.le(c('$distance', c('$position', colony, now), c('$position', L('other'), now)), g.mul(L('range'), L('range'))),
                  IF(g.both(g.le(F(action, 'value'), g.mget(F(colony, 'inventory'), F(action, 'text'))),
                            g.le(g.add(g.mget(F(L('other'), 'inventory'), F(action, 'text')), F(action, 'value')), c('$storage-limit', L('other')))),
                    LET([('paid', g.copy('Colony', colony, inventory=c('$pay-item', F(colony, 'inventory'), F(action, 'text'), F(action, 'value')))),
                         ('received', g.copy('Colony', L('other'), inventory=c('$item-credit', F(L('other'), 'inventory'), F(action, 'text'), F(action, 'value')))),
                         ('sent-world', c('$replace-colony', world, L('paid')))], success(L('sent-world'), L('received'))),
                    fail(world, 'transfer_cost')), fail(world, 'out_of_range'))), fail(world, 'neighbor_missing')))
    g.fn('action-transfer', {'world': '@World', 'colony': '@Colony', 'action': '@Action', 'now': 'i64'}, '@ActionResult', transfer)

    def dispatch(world, colony, action, now):
        fallback = fail(world, 'invalid_action')
        choices = [
            ('move', c('$action-move', world, colony, action, now)),
            ('research', IF(g.less(F(action, 'index'), I(96)), c('$action-research', world, colony, action), fallback)),
            ('build', IF(g.both(g.less(F(action, 'index'), I(8)), g.less(F(action, 'value'), I(72))), c('$action-build', world, colony, action, now), fallback)),
            ('transfer', c('$action-transfer', world, colony, action, now)),
            ('rename', IF(g.both(g.less(I(0), c('text-length', F(action, 'text'))), g.le(c('text-length', F(action, 'text')), I(32))),
                          success(world, g.copy('Colony', colony, name=F(action, 'text'))), fail(world, 'invalid_name'))),
        ] + [(op, c('$action-edit-building', world, colony, action)) for op in ['recipe', 'pause', 'repair', 'dismantle']]
        result = fallback
        for op, body in reversed(choices):
            result = IF(g.text_eq(F(action, 'op'), I(op)), body, result)
        return result
    g.fn('dispatch-action', {'world': '@World', 'colony': '@Colony', 'action': '@Action', 'now': 'i64'}, '@ActionResult', dispatch)
