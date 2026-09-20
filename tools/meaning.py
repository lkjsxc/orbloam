"""Small build-time notation for public structural lkjscript authoring; no evaluator."""
from __future__ import annotations
from build import lit, loc, rec, field, choose, let, seq
from catalog import RECIPES, RESEARCH

I = lit
L = loc
F = field
R = rec
IF = choose
LET = let
SEQ = seq


class Game:
    def __init__(self, author):
        self.a = author
        self.c = author.call
        self.fn = author.fn
        self.types = author.types

    def copy(self, ty, value, **changes):
        return rec(**{name: changes.get(name, F(value, name)) for name in self.types[ty]})

    def list(self, ty, *items):
        return f'(list {ty}' + (' ' + ' '.join(items) if items else '') + ')'

    def map(self, key='text', value='i64', **items):
        return f'(map {key} {value} ' + ' '.join(f'(entry {I(k)} {I(v)})' for k, v in items.items()) + ')'

    def get(self, values, index, ty):
        return self.c('list-get', values, index, types=(ty,))

    def length(self, values, ty):
        return self.c('list-length', values, types=(ty,))

    def append(self, values, value, ty):
        return self.c('list-append', values, value, types=(ty,))

    def mget(self, values, key, fallback=I(0), value='i64'):
        return self.c('map-get-or', values, key, fallback, types=('text', value))

    def mset(self, values, key, item, value='i64'):
        return self.c('map-insert', values, key, item, types=('text', value))

    def mremove(self, values, key, value):
        return self.c('map-remove', values, key, types=('text', value))

    def fold(self, item, state, items, initial, function):
        return self.c('list-fold-left', items, initial, f'(function-value ${function})', types=(item, state))

    def eq(self, x, y):
        return self.c('i64-equal', x, y)

    def text_eq(self, x, y):
        return self.c('text-equal', x, y)

    def add(self, *args):
        if not args:
            return I(0)
        expression = args[0]
        for arg in args[1:]:
            expression = self.c('add', expression, arg)
        return expression

    def sub(self, x, y):
        return self.c('subtract', x, y)

    def mul(self, x, y):
        return self.c('multiply', x, y)

    def div(self, x, y):
        return self.c('divide', x, y)

    def mod(self, x, y):
        return self.c('$mod', x, y)

    def low(self, x, y):
        return self.c('$min', x, y)

    def high(self, x, y):
        return self.c('$max', x, y)

    def less(self, x, y):
        return self.c('less', x, y)

    def le(self, x, y):
        return self.c('less-equal', x, y)

    def both(self, *conditions):
        result = I(True)
        for condition in reversed(conditions):
            result = IF(condition, result, I(False))
        return result

    def either(self, *conditions):
        result = I(False)
        for condition in reversed(conditions):
            result = IF(condition, I(True), result)
        return result

    def concat(self, x, y):
        return self.c('text-concat', x, y)

    def decimal(self, x):
        return self.c('i64-to-text', x)

    def rank(self, colony, branch):
        branch = I(branch) if isinstance(branch, int) else branch
        return self.mget(F(colony, 'research'), self.decimal(branch))

    def inv(self, colony, item):
        return self.mget(F(colony, 'inventory'), I(item) if isinstance(item, str) and not item.startswith('(') else item)

    def literal_record(self, fields):
        return R(**{key: I(value) for key, value in fields.items()})

    def table(self, name, records, ty):
        def tree(index, lo, hi):
            if hi - lo == 1:
                return self.literal_record(records[lo])
            mid = (lo + hi) // 2
            return IF(self.less(index, I(mid)), tree(index, lo, mid), tree(index, mid, hi))
        self.fn(name, {'index': 'i64'}, ty, lambda index: tree(index, 0, len(records)))

    def schema(self):
        a = self.a
        self.fn('min', {'a': 'i64', 'b': 'i64'}, 'i64', lambda x, y: IF(self.less(x, y), x, y))
        self.fn('max', {'a': 'i64', 'b': 'i64'}, 'i64', lambda x, y: IF(self.less(x, y), y, x))
        self.fn('abs', {'x': 'i64'}, 'i64', lambda x: IF(self.less(x, I(0)), self.sub(I(0), x), x))
        self.fn('mod', {'x': 'i64', 'n': 'i64'}, 'i64', lambda x, n:
                LET([('r', self.sub(x, self.mul(self.div(x, n), n)))],
                    IF(self.less(L('r'), I(0)), self.add(L('r'), n), L('r'))))
        self.fn('floor-cell', {'x': 'i64'}, 'i64', lambda x: self.div(self.sub(x, self.mod(x, I(128))), I(128)))
        a.structure('Point', {'x': 'i64', 'y': 'i64'})
        a.map_type('Inventory', 'text', 'i64')
        a.map_type('Receipts', 'text', 'text')
        a.structure('Cohort', {'first': 'i64', 'count': 'i64', 'start': 'i64'})
        a.list_type('Cohorts', '@Cohort')
        a.structure('Building', {'id': 'i64', 'kind': 'i64', 'recipe': 'i64', 'x': 'i64', 'y': 'i64',
                                  'health': 'i64', 'progress': 'i64', 'produced': 'i64', 'enabled': 'bool', 'status': 'text'})
        a.list_type('Buildings', '@Building')
        a.structure('Route', {'job': 'i64', 'x': 'i64', 'y': 'i64', 'tier': 'i64', 'units': 'i64', 'workers': 'i64'})
        a.list_type('Routes', '@Route')
        a.structure('Colony', {'id': 'i64', 'name': 'text', 'created_tick': 'i64', 'from_x': 'i64', 'from_y': 'i64', 'to_x': 'i64', 'to_y': 'i64',
                                'move_at': 'i64', 'move_ms': 'i64', 'cohorts': '@Cohorts', 'inventory': '@Inventory',
                                'research': '@Inventory', 'buildings': '@Buildings', 'routes': '@Routes',
                                'essence': 'i64', 'experience': 'i64', 'deaths': 'i64', 'gathered': 'i64',
                                'conversations': 'i64', 'neighbor': 'i64', 'next_building': 'i64',
                                'sequence': 'i64', 'last_intent': 'text', 'receipts': '@Receipts'})
        a.list_type('Colonies', '@Colony')
        a.structure('Node', {'stock': 'i64', 'tick': 'i64', 'x': 'i64', 'y': 'i64', 'kind': 'i64', 'tier': 'i64'})
        a.map_type('Nodes', 'text', '@Node')
        a.structure('World', {'version': 'i64', 'tick': 'i64', 'next_id': 'i64', 'colonies': '@Colonies', 'nodes': '@Nodes'})
        a.structure('Recipe', {key: ('text' if isinstance(value, str) else 'i64') for key, value in RECIPES[0].items()})
        a.structure('Research', {key: ('text' if isinstance(value, str) else 'i64') for key, value in RESEARCH[0].items()})
        a.structure('Envelope', {'me': 'i64', 'world': '@World', 'now_ms': 'i64', 'backlog_ticks': 'i64'})
        self.table('recipe-rule', RECIPES, '@Recipe')
        self.table('research-rule', RESEARCH, '@Research')
        self.fn('empty-world', {'tick': 'i64'}, '@World', lambda tick:
                R(version=I(1), tick=tick, next_id=I(1), colonies=self.list('@Colony'), nodes='(map text @Node)'))
        self.fn('new-colony', {'id': 'i64', 'name': 'text', 'tick': 'i64'}, '@Colony', self.new_colony)
        self.fn('position', {'colony': '@Colony', 'ms': 'i64'}, '@Point', self.position)
        self.fn('distance', {'a': '@Point', 'b': '@Point'}, 'i64', lambda x, y:
                self.add(self.mul(self.sub(F(x, 'x'), F(y, 'x')), self.sub(F(x, 'x'), F(y, 'x'))),
                         self.mul(self.sub(F(x, 'y'), F(y, 'y')), self.sub(F(x, 'y'), F(y, 'y')))))
        self.fn('level', {'colony': '@Colony'}, 'i64', lambda c: self.add(I(1), self.div(F(c, 'experience'), I(250))))
        self.fn('radius', {'colony': '@Colony'}, 'i64', lambda c: self.add(I(190), self.mul(self.rank(c, 1), I(24))))
        self.fn('storage-limit', {'colony': '@Colony'}, 'i64', lambda c: self.add(I(1000000), self.mul(self.rank(c, 6), I(500000))))
        self.fn('item-credit', {'inventory': '@Inventory', 'key': 'text', 'amount': 'i64'}, '@Inventory',
                lambda inv, key, amount: self.mset(inv, key, self.add(self.mget(inv, key), amount)))
        self.fn('replace-colony-loop', {'items': '@Colonies', 'colony': '@Colony', 'i': 'i64', 'out': '@Colonies'}, '@Colonies',
                lambda items, colony, i, out: IF(self.less(i, self.length(items, '@Colony')),
                    LET([('old', self.get(items, i, '@Colony'))], self.c('$replace-colony-loop', items, colony, self.add(i, I(1)),
                         self.append(out, IF(self.eq(F(L('old'), 'id'), F(colony, 'id')), colony, L('old')), '@Colony'))), out))
        self.fn('replace-colony', {'world': '@World', 'colony': '@Colony'}, '@World', lambda w, c:
                self.copy('World', w, colonies=self.c('$replace-colony-loop', F(w, 'colonies'), c, I(0), self.list('@Colony'))))

    def new_colony(self, identifier, name, tick):
        x = self.mul(self.sub(self.mod(self.sub(identifier, I(1)), I(8)), I(3)), I(72))
        y = self.mul(self.div(self.sub(identifier, I(1)), I(8)), I(72))
        return R(id=identifier, name=name, created_tick=tick, from_x=x, from_y=y, to_x=x, to_y=y, move_at=self.mul(tick, I(10000)), move_ms=I(1),
                 cohorts=self.list('@Cohort', R(first=I(0), count=I(16), start=self.sub(tick, I(3)))),
                 inventory=self.map(timber=80, stone=60, fiber=30, grain=40, ore=20, clay=20, crystal=10, water=50),
                 research=self.map(), buildings=self.list('@Building'), routes=self.list('@Route'),
                 essence=I(120), experience=I(0), deaths=I(0), gathered=I(0), conversations=I(0), neighbor=I(0),
                 next_building=I(1), sequence=I(0), last_intent=I(''), receipts='(map text text)')

    def position(self, colony, ms):
        return LET([('duration', self.high(I(1), F(colony, 'move_ms'))),
                    ('elapsed', self.low(L('duration'), self.high(I(0), self.sub(ms, F(colony, 'move_at')))))],
                   R(**{axis: self.add(F(colony, 'from_' + axis), self.div(self.mul(
                       self.sub(F(colony, 'to_' + axis), F(colony, 'from_' + axis)), L('elapsed')), L('duration')))
                       for axis in ['x', 'y']}))
