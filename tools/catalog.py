"""Versioned game content. Both native rules and UI discovery consume this catalogue."""
from __future__ import annotations

RAW = ['timber', 'stone', 'fiber', 'grain', 'ore', 'clay', 'crystal', 'water']
RAW_NAMES = ['原木', '石材', '繊維', '穀物', '鉱石', '粘土', '結晶', '水']
COLORS = ['#72cda0', '#b1bacc', '#d0bc87', '#e5bc68', '#c496a0', '#d79b7a', '#a998eb', '#79c9e3']
BRANCHES = [
    ('vitality', '生命', '新しい住民の席。ひとつの世代から、次の世代へ。', '#7bd1ab'),
    ('reach', '探索', 'コアの移動速度・採集範囲・扱える資源の階位を広げる。', '#82bee9'),
    ('harvest', '採集', '住民一人ひとりの採集量を増やす。', '#ddc77a'),
    ('industry', '工業', '工房の数と高度な加工技術を解放する。', '#d49781'),
    ('agronomy', '農学', '製粉と温室。穀物から豊かな食卓へ。', '#99c983'),
    ('aquaculture', '養殖', '海をつくらず、小さな養殖池で生命を育てる。', '#7fcdd6'),
    ('memory', '記憶', '世代から還るエッセンスと、倉庫の容量を増やす。', '#b1a0ee'),
    ('fellowship', '交流', '隣人との対話と、物資を分け合う範囲を広げる。', '#df9fc1'),
]
INDUSTRIES = [
    ('sawmill', '製材所', 3, 0), ('kiln', '窯', 3, 1),
    ('smelter', '精錬所', 3, 2), ('loom', '織物工房', 3, 1),
    ('mill', '製粉所', 4, 0), ('greenhouse', '温室', 4, 1),
    ('hatchery', '養殖池', 5, 1), ('atelier', '精密工房', 3, 3),
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
PRODUCT_NAMES = [
    ['板材', '梁', '積層材', '硬質材', '樹脂材', '構造材', '生きた木材', '共鳴材', '心樹材'],
    ['レンガ', 'タイル', 'ガラス', '陶材', '磁器', '絶縁材', '結晶ガラス', 'レンズ', 'プリズム'],
    ['金属塊', '鋼', '合金', '線材', 'ばね', '導体', '精密合金', '流動金属', '星金属'],
    ['布', '縄', '帆布', 'フェルト', '絹', 'メッシュ', 'フィラメント', '機能繊維', '記憶織物'],
    ['小麦粉', 'パン', 'ビスケット', '保存食', '発酵種', '培養種', '栄養素', '祝祭食', '生命食'],
    ['野菜', '薬草', '果実', '植物油', '染料', '薬', '抽出液', '触媒', '生命培養体'],
    ['魚', '燻製魚', '魚粉', '貝殻', '真珠', 'サンゴ', '生物濾材', '水生酵素', '光真珠'],
    ['道具', '歯車', 'ポンプ', '原動機', 'センサー', '制御器', '自動機', '共鳴器', '世界の種'],
]
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
ITEMS.append({'key': 'insight', 'name': '交流の記録', 'color': '#df9fc1', 'tier': 0})
RESEARCH = []
for branch in range(8):
    for tier in range(1, 13):
        item = PRODUCT_KEYS[branch][min(8, tier - 4)] if tier >= 4 else ''
        RESEARCH.append({'id': branch * 12 + tier - 1, 'branch': branch, 'tier': tier,
                         'essence': 12 + tier * tier * 8 + branch * 3,
                         'raw': RAW[branch], 'raw_amount': 20 * tier * tier,
                         'product': item, 'product_amount': tier + 2 if item else 0})

CATALOG = {
    'name': 'Orbloam', 'version': 1, 'tagline': '小さな命が、大きな文明をつくる。',
    'step_ms': 10000, 'lifespan_ticks': 360, 'cell_size': 128, 'world_bound': 1000000,
    'maximum_cores': 64, 'maximum_deposits': 4096,
    'items': ITEMS, 'raw': RAW, 'recipes': RECIPES, 'research': RESEARCH,
    'branches': [{'id': i, 'key': k, 'name': n, 'description': d, 'color': col}
                 for i, (k, n, d, col) in enumerate(BRANCHES)],
    'industries': [{'id': i, 'key': key, 'name': name, 'branch': branch, 'rank': rank,
                    'timber': 30 + i * 8, 'stone': 20 + i * 5}
                   for i, (key, name, branch, rank) in enumerate(INDUSTRIES)],
}
assert len(RECIPES) == 72 and len(RESEARCH) == 96
assert len({i['key'] for i in ITEMS}) == len(ITEMS)
