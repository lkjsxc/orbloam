"""Compose the native Orbloam graph; Python authors records but never runs a world."""
from meaning import Game, I, L, F, R, LET
import population
import gathering
import factories
import simulation
import actions
import service
import probes
import probe_pages


def compose(author):
    g = Game(author)
    g.schema()
    population.compose(g)
    gathering.compose(g)
    author.stages = [('ecology', len(author.records))]
    factories.compose(g)
    simulation.compose(g)
    actions.compose(g)
    author.stages.append(('industry-and-actions', len(author.records)))
    service.compose(g)
    g.fn('population-probe', {'count': 'i64', 'tick': 'i64'}, '@Population', lambda n, tick:
         LET([('colony', g.c('$new-colony', I(1), I('probe'), I(0)))],
             g.c('$population', g.copy('Colony', L('colony'),
                  cohorts=g.list('@Cohort', R(first=I(0), count=n, start=I(0)))), tick)))
    author.port('population-probe', 'population-probe', target='population-probe')
    author.stages.append(('service-and-client', len(author.records)))
    probes.compose(g)
    author.stages.append(('verification-probes', len(author.records)))
    probe_pages.compose(g)
    author.stages.append(('bounded-verification-pages', len(author.records)))
