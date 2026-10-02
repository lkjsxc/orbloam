"""Independent enumerative oracle: individual lives and a brute-force spatial scan.

This is a test oracle only. It neither serves HTTP nor runs in the playable package.
It deliberately does not reuse the native author's cohort formulas or modular-cell scan.
"""
from __future__ import annotations
import copy

RAW = ['timber', 'stone', 'fiber', 'grain', 'ore', 'clay', 'crystal', 'water']


def world_from_wire(world):
    world = copy.deepcopy(world)
    world['nodes'] = dict(world['nodes'])
    for colony in world['colonies']:
        for field in ['inventory', 'research', 'receipts']:
            colony[field] = dict(colony[field])
    return world


def population(cohorts, tick):
    people = []
    deaths = 0
    for cohort in cohorts:
        for offset in range(cohort['count']):
            birthday = cohort['start'] + offset
            if birthday <= tick:
                people.append(cohort['first'] + offset)
                deaths += int(tick > birthday and (tick - birthday) % 90 == 0)
    return {'tick': tick, 'count': len(people), 'capacity': sum(c['count'] for c in cohorts),
            'deaths': deaths, 'roles': {str(role): sum(person % 10 == role for person in people) for role in range(10)}}


def deaths_between(cohorts, start, end):
    return sum(max(0, (end - group['start'] - slot) // 90) - max(0, (start - group['start'] - slot) // 90)
               for group in cohorts for slot in range(group['count']))


def trunc_div(n, d):
    return (abs(n) // abs(d)) * (-1 if (n < 0) != (d < 0) else 1)


def position(colony, milliseconds):
    duration = max(1, colony['move_ms'])
    elapsed = min(duration, max(0, milliseconds - colony['move_at']))
    return tuple(colony['from_' + axis] + trunc_div((colony['to_' + axis] - colony['from_' + axis]) * elapsed, duration)
                 for axis in ['x', 'y'])


def terrain(cx, cy, tick):
    salt = (cx * 92821 + cy * 68917 + 19139) % 2147483647
    tier = 1 + max(abs(cx), abs(cy)) // 8
    return {'stock': 180 + 30 * tier, 'tick': tick, 'x': cx * 128 + 24 + salt % 80,
            'y': cy * 128 + 24 + (salt // 97) % 80, 'kind': (cx + 3 * cy) % 8, 'tier': tier}


def available(node, tick):
    return min(180 + 30 * node['tier'], node['stock'] + max(0, tick - node['tick']) * (2 + node['tier'] // 3))


def gather_only_step(before, catalogue=None):
    """Independent world step: enumerate lives, every candidate cell, and recipes."""
    world = copy.deepcopy(before)
    tick = world['tick'] + 1
    if tick % 36 == 0:
        world['nodes'] = {k: v for k, v in world['nodes'].items() if available(v, tick) < 180 + 30 * v['tier']}
    size = len(world['colonies'])
    for ordinal in range(size):
        index = (tick + ordinal) % size
        colony = world['colonies'][index]
        if colony['created_tick'] > tick:
            continue
        if colony['buildings'] and catalogue is None:
            raise AssertionError('Workshop oracle requires the native-served catalogue')
        people = population(colony['cohorts'], tick)
        rank = lambda branch: colony['research'].get(str(branch), 0)
        radius = 190 + 24 * rank(1)
        tier_limit = 1 + 2 * rank(1) + (1 + colony['experience'] // 250) // 25
        storage = 1000000 + 500000 * rank(6)
        px, py = position(colony, tick * 10000)
        routes, gathered = [], 0
        for job, item in enumerate(RAW):
            candidates = []
            # Unlike the native implementation, visit EVERY grid cell for each role.
            for cy in range((py - radius) // 128, (py + radius) // 128 + 1):
                for cx in range((px - radius) // 128, (px + radius) // 128 + 1):
                    key = f'{cx}:{cy}'
                    generated = terrain(cx, cy, tick)
                    distance = (generated['x'] - px) ** 2 + (generated['y'] - py) ** 2
                    node = world['nodes'].get(key, generated)
                    if (generated['kind'] == job and generated['tier'] <= tier_limit and distance <= radius ** 2
                            and (key in world['nodes'] or len(world['nodes']) < 4096) and available(node, tick) > 0):
                        candidates.append((distance, cy, cx, key, node))
            if not candidates:
                continue
            _, _, _, key, node = min(candidates, key=lambda entry: entry[:3])
            workers = people['roles'][str(job)]
            wanted = (1 + workers * (1 + rank(2))) * node['tier']
            stock = available(node, tick)
            take = max(0, min(stock, wanted, storage - colony['inventory'].get(item, 0)))
            colony['inventory'][item] = colony['inventory'].get(item, 0) + take
            if take > 0:
                world['nodes'][key] = dict(node, tick=tick, stock=stock - take)
            routes.append({'job': job, 'x': node['x'], 'y': node['y'], 'tier': node['tier'], 'units': take, 'workers': workers})
            gathered += take
        colony['routes'] = routes
        machine_experience = factory_step(colony, people, tick, catalogue) if colony['buildings'] else 0
        colony['gathered'] += gathered
        colony['experience'] += gathered + machine_experience
        colony['deaths'] += people['deaths']
        colony['essence'] += people['deaths'] * (6 + 2 * rank(6))
        if tick % 6 == 0:
            neighbor = next((other for other in world['colonies'] if other['id'] != colony['id'] and other['created_tick'] <= tick
                and sum((a - b) ** 2 for a, b in zip(position(other, tick * 10000), (px, py))) <= (300 + 50 * rank(7)) ** 2), None)
            colony['neighbor'] = neighbor['id'] if neighbor else 0
            if neighbor:
                colony['conversations'] += 1
                colony['experience'] += 2 + rank(7)
                colony['inventory']['insight'] = min(storage, colony['inventory'].get('insight', 0) + 1)
    world['tick'] = tick
    return world


def factory_step(colony, people, tick, catalogue):
    """Brute-force scheduling + conservative batches, no imported author formulas."""
    stock, ranks = colony['inventory'], colony['research']
    workers = people['roles']['8'] + people['roles']['9']
    storage = 1000000 + 500000 * ranks.get('6', 0)
    radius = 2 * (190 + 24 * ranks.get('1', 0))
    px, py = position(colony, tick * 10000)
    experience = 0
    for building in colony['buildings']:
        manual = ranks.get('manual:' + str(building['id']), 0) == 1
        progressing = building['progress'] > 0 and building['status'] == 'working'
        choice = building['recipe']
        if not manual and not progressing:
            eligible = []
            for recipe in catalogue['recipes']:
                if recipe['kind'] != building['kind'] or recipe['rank'] > ranks.get(str(recipe['branch']), 0):
                    continue
                amount = recipe['amount'] * (1 + ranks.get(str(recipe['branch']), 0) // 4)
                if stock.get(recipe['output'], 0) + amount > storage:
                    continue
                if any(stock.get(recipe[k], 0) < recipe['n' + k] for k in ['a', 'b', 'c']):
                    continue
                coverage = stock.get(recipe['output'], 0) * 1000 // (12 * (recipe['tier'] + 1))
                eligible.append((coverage, recipe['id']))
            if eligible:
                choice = min(eligible)[1]
        if choice != building['recipe']:
            building['recipe'], building['progress'] = choice, 0
        rule = catalogue['recipes'][choice]
        near = (building['x'] - px)**2 + (building['y'] - py)**2 <= radius**2
        if tick % 6 == 0:
            if near and workers > 0 and stock.get('timber', 0) >= 1 and stock.get('stone', 0) >= 1:
                stock['timber'] -= 1; stock['stone'] -= 1
                building['health'] = min(100, building['health'] + 1)
            else:
                building['health'] = max(0, building['health'] - 2)
        if not building['enabled']: building['status'] = 'paused'
        elif not near: building['status'] = 'distant'
        elif building['health'] <= 0: building['status'] = 'maintenance'
        elif workers < rule['workers']: building['status'] = 'workers'
        else:
            workers -= rule['workers']
            building['status'] = 'working'
            if building['progress'] + 1 < rule['period']:
                building['progress'] += 1
                continue
            if any(stock.get(rule[k], 0) < rule['n' + k] for k in ['a', 'b', 'c']):
                building['status'] = 'materials'; continue
            amount = rule['amount'] * (1 + ranks.get(str(rule['branch']), 0) // 4)
            if stock.get(rule['output'], 0) + amount > storage:
                building['status'] = 'warehouse'; continue
            for k in ['a', 'b', 'c']:
                if rule['n' + k]: stock[rule[k]] = stock.get(rule[k], 0) - rule['n' + k]
            stock[rule['output']] = stock.get(rule['output'], 0) + amount
            building['produced'] += amount
            building['progress'] = 0
            experience += rule['tier'] * 4
    return experience


def assert_probe(report, catalogue):
    counts, ticks = [0, 1, 16, 256, 512, 4096], [-1, 0, 1, 89, 90, 105, 180, 1024]
    assert len(report['populations']) == len(counts) * len(ticks)
    for index, result in enumerate(report['populations']):
        count, tick = counts[index // len(ticks)], ticks[index % len(ticks)]
        actual = dict(result, roles=dict(result['roles']))
        expected = population([{'first': 0, 'count': count, 'start': 0}], tick)
        assert actual == expected, ('population', count, tick, actual, expected)
    assert len(report['machines']) == 72
    for result, rule in zip(report['machines'], catalogue['recipes']):
        assert result['id'] == rule['id']
        before = {item['key']: 100 for item in catalogue['items']}
        expected = dict(before)
        for letter in ['a', 'b', 'c']:
            if rule['n' + letter]:
                expected[rule[letter]] -= rule['n' + letter]
        amount = rule['amount'] * 3  # The fixture explicitly grants rank 8, not real earned research.
        expected[rule['output']] += amount
        ready = result['ready']
        assert dict(ready['inventory']) == expected, ('recipe-conservation', rule['id'])
        assert ready['building']['produced'] == amount and ready['building']['progress'] == 0
        assert ready['experience'] == 4 * rule['tier'] and ready['building']['status'] == 'working'
        blocked = result['blocked']
        assert blocked['inventory'] == [] and blocked['building']['produced'] == 0
        assert blocked['building']['progress'] == rule['period'] - 1 and blocked['building']['status'] == 'materials'
        warehouse = result['warehouse']
        expected_full = dict(before, **{rule['output']: 1000000})
        assert dict(warehouse['inventory']) == expected_full
        assert warehouse['building']['produced'] == 0 and warehouse['building']['progress'] == rule['period'] - 1
        assert warehouse['building']['status'] == 'warehouse' and warehouse['experience'] == 0
    before, after = world_from_wire(report['before']), world_from_wire(report['after'])
    expected = gather_only_step(before)
    assert after == expected, ('independent-shared-world-step', after, expected)
    assert report['split_equal'] is True
    return {'enumerative_population_cases': len(counts) * len(ticks), 'native_recipe_cases': 72,
            'recipe_paths_per_case': ['completion', 'missing-input', 'full-warehouse'],
            'shared_world_cores': len(before['colonies']), 'inhabitants_per_core': 512,
            'full_world_equal_to_independent_oracle': True, 'split_canonical_world_equal': True}
