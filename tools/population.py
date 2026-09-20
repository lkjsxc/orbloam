"""Exact arithmetic cohorts, not average populations or statistical simulation."""
from meaning import I, L, F, R, IF, LET


def compose(g):
    a, c = g.a, g.c
    a.structure('Population', {'tick': 'i64', 'count': 'i64', 'capacity': 'i64', 'deaths': 'i64', 'roles': '@Inventory'})
    g.fn('active-count', {'cohort': '@Cohort', 'tick': 'i64'}, 'i64', lambda group, tick:
         g.low(F(group, 'count'), g.high(I(0), g.add(g.sub(tick, F(group, 'start')), I(1)))))
    g.fn('role-prefix', {'count': 'i64', 'role': 'i64'}, 'i64', lambda n, role:
         g.high(I(0), g.div(g.sub(g.add(n, I(9)), role), I(10))))
    g.fn('cohort-deaths', {'cohort': '@Cohort', 'tick': 'i64'}, 'i64', lambda group, tick:
         LET([('age', g.sub(tick, F(group, 'start'))),
              ('residue', g.mod(L('age'), I(360))),
              ('eligible', g.low(F(group, 'count'), g.sub(L('age'), I(359))))],
             IF(g.less(L('residue'), L('eligible')),
                g.add(I(1), g.div(g.sub(g.sub(L('eligible'), I(1)), L('residue')), I(360))), I(0))))

    def population_step(state, group):
        roles = F(state, 'roles')
        for job in range(10):
            roles = g.mset(roles, I(str(job)), g.add(g.mget(F(state, 'roles'), I(str(job))),
                g.sub(c('$role-prefix', g.add(F(group, 'first'), L('active')), I(job)),
                      c('$role-prefix', F(group, 'first'), I(job)))))
        return LET([('active', c('$active-count', group, F(state, 'tick')))],
                   R(tick=F(state, 'tick'), count=g.add(F(state, 'count'), L('active')),
                     capacity=g.add(F(state, 'capacity'), F(group, 'count')),
                     deaths=g.add(F(state, 'deaths'), c('$cohort-deaths', group, F(state, 'tick'))), roles=roles))
    g.fn('population-step', {'state': '@Population', 'cohort': '@Cohort'}, '@Population', population_step)
    g.fn('population', {'colony': '@Colony', 'tick': 'i64'}, '@Population', lambda colony, tick:
         g.fold('@Cohort', '@Population', F(colony, 'cohorts'),
                R(tick=tick, count=I(0), capacity=I(0), deaths=I(0), roles=g.map()), 'population-step'))
    group = R(first=I(0), count=I(16), start=I(0))
    for tick, expected in [(0, 0), (359, 0), (360, 1), (375, 1), (376, 0), (720, 1)]:
        a.test('lifetime-' + str(tick), c('$cohort-deaths', group, I(tick)), I(expected))
    a.test('overlapping-generations', c('$cohort-deaths', R(first=I(0), count=I(512), start=I(0)), I(720)), I(2))
    a.test('staggered-births', c('$active-count', group, I(4)), I(5))
    a.test('not-born-yet', c('$active-count', group, I(-1)), I(0))
    for job in range(10):
        a.test('role-' + str(job), c('$role-prefix', I(512), I(job)), I(len(range(job, 512, 10))))
