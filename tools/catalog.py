"""Versioned game content. Both native rules and UI discovery consume this catalogue."""
from __future__ import annotations

RAW = ['timber', 'stone', 'fiber', 'grain', 'ore', 'clay', 'crystal', 'water']
RAW_NAMES = ['Timber', 'Stone', 'Fiber', 'Grain', 'Ore', 'Clay', 'Crystal', 'Water']
COLORS = ['#72cda0', '#b1bacc', '#d0bc87', '#e5bc68', '#c496a0', '#d79b7a', '#a998eb', '#79c9e3']
BRANCHES = [
    ('vitality', 'Vitality', 'Make room for new lives. Each discovery adds 48 resident places.', '#7bd1ab'),
    ('reach', 'Reach', 'Travel faster, gather farther, and work richer deposits.', '#82bee9'),
    ('harvest', 'Harvest', 'Help every gatherer bring more home.', '#ddc77a'),
    ('industry', 'Industry', 'More workshops, deeper production chains, better yields.', '#d49781'),
    ('agronomy', 'Agronomy', 'Cultivate food, medicines, and living materials.', '#99c983'),
    ('aquaculture', 'Aquaculture', 'Nurture small ponds, pearls, and aquatic life.', '#7fcdd6'),
    ('memory', 'Memory', 'Receive more Essence from each life and keep larger stores.', '#b1a0ee'),
    ('fellowship', 'Fellowship', 'Meet neighbors and share across greater distances.', '#df9fc1'),
]
INDUSTRIES = [
    ('sawmill', 'Sawmill', 3, 0), ('kiln', 'Kiln', 3, 1),
    ('smelter', 'Smelter', 3, 2), ('loom', 'Weavery', 3, 1),
    ('mill', 'Mill', 4, 0), ('greenhouse', 'Greenhouse', 4, 1),
    ('hatchery', 'Hatchery', 5, 1), ('atelier', 'Atelier', 3, 3),
]
PRODUCT_KEYS = [
    ['plank', 'beam', 'laminate', 'hardwood', 'resinwood', 'engineered-wood', 'living-wood', 'harmonic-wood', 'heartwood'],
    ['brick', 'tile', 'glass', 'ceramic', 'porcelain', 'insulator', 'crystal-glass', 'lens', 'prism'],
    ['ingot', 'steel', 'alloy', 'wire', 'spring', 'conductor', 'precision-alloy', 'flux-metal', 'star-metal'],
    ['cloth', 'rope', 'canvas', 'felt', 'silk', 'mesh', 'filament', 'smart-fabric', 'memory-weave'],
    ['flour', 'bread', 'biscuit', 'ration', 'ferment', 'culture', 'nutrient', 'feast', 'ambrosia'],
    ['vegetable', 'herb', 'fruit', 'oil', 'dye', 'medicine', 'extract', 'catalyst', 'life-culture'],
    ['fish', 'smoked-fish', 'fish-meal', 'shell', 'pearl', 'coral', 'biofilter', 'marine-enzyme', 'luminous-pearl'],
    ['tool', 'gear', 'pump', 'motor', 'sensor', 'controller', 'automaton', 'resonator', 'world-seed'],
]
PRODUCT_NAMES = [[key.replace('-', ' ').title() for key in group] for group in PRODUCT_KEYS]
BASE_INPUTS = [
    [('timber', 4)], [('clay', 3), ('stone', 1)], [('ore', 3), ('timber', 2)],
    [('fiber', 4)], [('grain', 4)], [('water', 3), ('grain', 1)],
    [('water', 4), ('grain', 2)], [('ingot', 2), ('plank', 2)],
]
RECIPES = []
ITEMS = [{'key': key, 'name': name, 'color': color, 'tier': 0} for key, name, color in zip(RAW, RAW_NAMES, COLORS)]
for kind in range(8):
    for tier in range(1, 10):
        product = PRODUCT_KEYS[kind][tier - 1]
        ITEMS.append({'key': product, 'name': PRODUCT_NAMES[kind][tier - 1], 'color': COLORS[kind], 'tier': tier})
        inputs = list(BASE_INPUTS[kind]) if tier == 1 else [(PRODUCT_KEYS[kind][tier - 2], 2), (RAW[kind], 2 + tier)]
        if tier >= 3:
            inputs.append((PRODUCT_KEYS[(kind + 1) % 8][tier - 3], 1))
        inputs += [('', 0)] * (3 - len(inputs))
        branch = INDUSTRIES[kind][2]
        RECIPES.append({'id': kind * 9 + tier - 1, 'kind': kind, 'tier': tier,
                        'branch': branch, 'rank': max(INDUSTRIES[kind][3], tier - 1),
                        'period': 2 + tier, 'workers': 1 + (tier - 1) // 3,
                        'output': product, 'amount': 2 if kind != 7 else 1,
                        'a': inputs[0][0], 'na': inputs[0][1], 'b': inputs[1][0], 'nb': inputs[1][1],
                        'c': inputs[2][0], 'nc': inputs[2][1]})
ITEMS.append({'key': 'insight', 'name': 'Shared insight', 'color': '#df9fc1', 'tier': 0})
RESEARCH = []
for branch in range(8):
    for tier in range(1, 13):
        item = PRODUCT_KEYS[branch][min(8, tier - 4)] if tier >= 4 else ''
        RESEARCH.append({'id': branch * 12 + tier - 1, 'branch': branch, 'tier': tier,
                         'essence': 12 + tier * tier * 8 + branch * 3,
                         'raw': RAW[branch], 'raw_amount': 20 * tier * tier,
                         'product': item, 'product_amount': tier + 2 if item else 0})

# Every family forks twice; leaves have explicit prerequisites, not a rank chain.
# IDs and original costs remain stable. Existing branch ranks are preserved by
# lazy per-family legacy baselines in progression.py.
PARENTS = [-1, 0, 0, 1, 1, 2, 2, 3, 4, 5, 6, 6]
DISCOVERIES = [
    ['First light', 'Kindred sparks', 'A wider circle', 'Bright beginnings', 'Shared shelter', 'Rooted lives', 'Gentle renewal', 'A thousand mornings', 'Constellation', 'Flourishing', 'Enduring light', 'Many little worlds'],
    ['Horizon', 'Wandering light', 'Long roots', 'Swift passage', 'Far-seeing', 'Open paths', 'Deep prospect', 'Beyond the grove', 'Distant stars', 'Wide embrace', 'Hidden abundance', 'Worldwalker'],
    ['Gathering', 'Careful hands', 'Full baskets', 'Fine tools', 'Wild plenty', 'Patient tending', 'Shared bounty', "Nature's measure", 'Abundance', 'Seasonal wisdom', 'Golden harvest', 'Living wealth'],
    ['Craft', 'Joinery', 'Fired earth', 'Metalwork', 'Fine weave', 'Mechanisms', 'Cooperation', 'Precision', 'Assembly', 'Automation', 'Resonance', 'Great works'],
    ['Cultivation', 'Garden beds', 'Milling', 'Herbalism', 'Orchards', 'Fermentation', 'Nourishment', 'Living pharmacy', 'Perennial gardens', 'Culture', 'The generous table', 'Verdant mastery'],
    ['Still water', 'Small ponds', 'Clear currents', 'Hatchlings', 'Shellcraft', 'Living filters', 'Pearl gardens', 'Coral nursery', 'Luminous waters', 'Aquatic symbiosis', 'Deep harmony', 'A living mosaic'],
    ['Remembrance', 'Keepsakes', 'Quiet wisdom', 'Stories', 'Archives', 'Long memory', 'Inner light', 'A life remembered', 'The great library', 'Dreaming', 'Ancestral glow', 'Timeless'],
    ['Neighborliness', 'Conversation', 'Open hands', 'Hospitality', 'Common ground', 'Wayfinding', 'Kinship', 'Shared stories', 'Gift circles', 'Fellow travelers', 'Together', 'A world of friends'],
]
CATALOG = {
    'name': 'Orbloam', 'version': 2, 'tagline': 'Little lives. A world of their own.',
    'step_ms': 10000, 'lifespan_ticks': 90, 'cell_size': 128, 'world_bound': 1000000,
    'maximum_cores': 64, 'maximum_deposits': 4096,
    'items': ITEMS, 'raw': RAW, 'recipes': RECIPES,
    'research': [dict(r, parent=(-1 if PARENTS[r['tier']-1] == -1 else r['branch']*12+PARENTS[r['tier']-1]),
                      name=DISCOVERIES[r['branch']][r['tier']-1]) for r in RESEARCH],
    'branches': [{'id': i, 'key': k, 'name': n, 'description': d, 'color': col}
                 for i, (k, n, d, col) in enumerate(BRANCHES)],
    'industries': [{'id': i, 'key': key, 'name': name, 'branch': branch, 'rank': rank,
                    'timber': 30 + i * 8, 'stone': 20 + i * 5}
                   for i, (key, name, branch, rank) in enumerate(INDUSTRIES)],
}
assert len(RECIPES) == 72 and len(RESEARCH) == 96
assert len({i['key'] for i in ITEMS}) == len(ITEMS)
