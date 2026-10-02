"""Native inventory-guided recipe selection. Never issues browser-side commands."""
from meaning import I, L, F, R, IF, LET


def compose(g):
    c = g.c
    g.a.structure('RecipeChoice', {'id': 'i64', 'score': 'i64'})
    # Lower output coverage gets priority. Tier-specific buffers stop finished
    # high-tier goods permanently outranking their necessary intermediates.
    def score(research, inventory, rule, storage):
        eligible = g.both(g.le(F(rule, 'rank'), g.mget(research, g.decimal(F(rule, 'branch')))),
            *(g.le(F(rule, 'n' + k), g.mget(inventory, F(rule, k))) for k in ['a', 'b', 'c']),
            g.le(g.add(g.mget(inventory, F(rule, 'output')), g.mul(F(rule, 'amount'),
                     g.add(I(1), g.div(g.mget(research, g.decimal(F(rule, 'branch'))), I(4))))), storage))
        return IF(eligible, g.div(g.mul(g.mget(inventory, F(rule, 'output')), I(1000)),
                         g.mul(I(12), g.add(I(1), F(rule, 'tier')))), I(1000000000000))
    g.fn('recipe-coverage', {'research': '@Inventory', 'inventory': '@Inventory', 'rule': '@Recipe', 'storage': 'i64'}, 'i64', score)
    def loop(research, inventory, start, end, storage, best):
        return IF(g.less(start, end),
            LET([('rule', c('$recipe-rule', start)), ('score', c('$recipe-coverage', research, inventory, L('rule'), storage)),
                 ('next', IF(g.less(L('score'), F(best, 'score')), R(id=start, score=L('score')), best))],
                 c('$automatic-recipe-loop', research, inventory, g.add(start, I(1)), end, storage, L('next'))), F(best, 'id'))
    g.fn('automatic-recipe-loop', {'research': '@Inventory', 'inventory': '@Inventory', 'index': 'i64', 'end': 'i64', 'storage': 'i64', 'best': '@RecipeChoice'}, 'i64', loop)
    def select(research, inventory, building, storage):
        manual = g.eq(g.mget(research, g.concat(I('manual:'), g.decimal(F(building, 'id')))), I(1))
        progressing = g.both(g.less(I(0), F(building, 'progress')), g.text_eq(F(building, 'status'), I('working')))
        return IF(g.either(manual, progressing), F(building, 'recipe'),
               LET([('start', g.mul(F(building, 'kind'), I(9)))],
                 c('$automatic-recipe-loop', research, inventory, L('start'), g.add(L('start'), I(9)), storage,
                   R(id=F(building, 'recipe'), score=I(1000000000000)))))
    g.fn('automatic-recipe', {'research': '@Inventory', 'inventory': '@Inventory', 'building': '@Building', 'storage': 'i64'}, 'i64', select)
    b = R(id=I(1), kind=I(0), recipe=I(0), x=I(0), y=I(0), health=I(100), progress=I(0),
          produced=I(0), enabled=I(True), status=I('working'))
    inv = g.map(timber=100, plank=50)
    research = g.map(**{'3': 1})
    g.a.test('automation-fills-missing-intermediate', c('$automatic-recipe', research, inv, b, I(1000000)), I(1))
    g.a.test('automation-respects-unlocks', c('$automatic-recipe', g.map(), inv, b, I(1000000)), I(0))
    g.a.test('automation-respects-manual', c('$automatic-recipe', g.map(**{'3': 1, 'manual:1': 1}), inv, b, I(1000000)), I(0))
    g.a.test('automation-keeps-work-in-progress', c('$automatic-recipe', research, inv, g.copy('Building', b, progress=I(1)), I(1000000)), I(0))
    g.a.test('automation-empty-stock-safe', c('$automatic-recipe', research, g.map(), b, I(1000000)), I(0))
