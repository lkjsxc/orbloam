import {GameAPI, errorText, loadLocal, saveLocal} from './api.js';
import {WorldScene, population, position, inhabitantName, clamp, mod} from './world.js';
import {ResearchTree} from './research.js';
const $ = id => document.getElementById(id);
const el = (tag, className, text) => { const node = document.createElement(tag); if (className) node.className = className; if (text !== undefined) node.textContent = text; return node; };
const format = n => Math.trunc(n || 0).toLocaleString('ja-JP');
let catalog, items = new Map(), entered = false, tab = 'inventory', selected = null, selectedResearch = null, giftRecipient = null;
let pollTimer = null, toastTimer = null, registration = null, pollActive = false;
const api = new GameAPI(onState, pending => { $('pending').classList.toggle('hidden', !pending); if (!pending && entered) { renderPanel(); renderSelection(); if (selectedResearch !== null) renderResearch(); } });
const scene = new WorldScene($('world'), pick);
const tree = new ResearchTree($('research-canvas'), index => { selectedResearch = index; renderResearch(); });
const me = () => api.state?.world.colonies.find(c => c.id === api.state.me);
const itemName = key => items.get(key)?.name || key;
const isBusy = () => !!api.pending || (api.state?.backlog_ticks || 0) > 0;
const inputFocused = container => container.contains(document.activeElement) && ['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement.tagName);
const statusName = {working: '稼働中', materials: '素材待ち', warehouse: '倉庫が満杯', workers: '工房職を待っています', maintenance: '修理が必要', distant: 'コアから離れています', paused: '停止中'};
function toast(message) { $('toast').textContent = message; $('toast').classList.remove('hidden'); clearTimeout(toastTimer); toastTimer = setTimeout(() => $('toast').classList.add('hidden'), 5000); }
function button(text, action, className = '') { const node = el('button', className, text); node.addEventListener('click', action); return node; }
function resource(key, amount) { const node = el('div', 'resource'), dot = el('span', 'resource-dot'), body = el('div');
  dot.style.background = items.get(key)?.color || '#abc9b7'; body.append(el('small', '', itemName(key)), el('b', '', format(amount))); node.append(dot, body); return node; }
function level(colony) { return 1 + Math.trunc(colony.experience / 250); }
function colonyById(id) { return api.state?.world.colonies.find(c => c.id === id); }
async function command(op, parameters = {}) {
  try { await api.command(op, parameters); if (op !== 'move') toast('操作を保存しました。'); return true; }
  catch (error) { toast(errorText(error)); return false; }
}
function mode(value, kind = 0) {
  scene.mode = value; scene.buildKind = kind;
  for (const name of ['inspect', 'move', 'build']) $(name + '-mode').classList.toggle('active', name === value);
  $('mode-hint').classList.toggle('hidden', value === 'inspect');
  $('mode-hint').textContent = value === 'build' ? `${catalog.industries[kind].name}を置く場所をクリック · 観察でキャンセル` : '移動先をクリック · 観察でキャンセル';
  $('world').style.cursor = value === 'inspect' ? 'grab' : 'crosshair';
}
function openPanel(name) { tab = name; $('sidebar').classList.remove('hidden'); renderPanel(); }
function onState(state) {
  scene.setState(state); const colony = me(); if (!colony) return;
  tree.setColony(colony); $('colony-name').textContent = colony.name; $('core-level').textContent = `CORE Lv.${format(level(colony))}`;
  const people = population(colony, state.world.tick); $('population').textContent = format(people.count);
  $('essence').textContent = format(colony.essence); $('generations').textContent = format(colony.deaths);
  let nextDeath = 360;
  for (const cohort of colony.cohorts) for (let i = 0; i < clamp(state.world.tick - cohort.start + 1, 0, cohort.count); i++) nextDeath = Math.min(nextDeath, 360 - mod(state.world.tick - cohort.start - i, 360));
  $('life-note').textContent = `${people.count}/${people.capacity}席 · 次の還生まで約${Math.max(1, Math.ceil(nextDeath / 6))}分。${people.count < people.capacity ? '10秒ごとに新しい住民が誕生します。' : '住民の仕事は自動で進みます。'}`;
  $('colony-count').textContent = `${state.world.colonies.length}のコアが暮らしています`;
  $('network').textContent = `${Math.round(api.latency)} ms`; $('status-dot').className = 'status-dot online';
  $('backlog').classList.toggle('hidden', state.backlog_ticks === 0);
  $('backlog-text').textContent = `残り ${format(state.backlog_ticks * 10)}秒分 · 時間は飛ばしません`;
  if (!inputFocused($('panel-content'))) renderPanel();
  if (selected && !inputFocused($('selection-body'))) renderSelection();
  if (selectedResearch !== null) renderResearch();
  $('research-progress').textContent = `${Object.values(colony.research).reduce((a, b) => a + b, 0)} / 96`;
}
function renderPanel() {
  if (!catalog || !me()) return; for (const node of document.querySelectorAll('[data-tab]')) node.classList.toggle('active', node.dataset.tab === tab);
  $('panel-title').textContent = {inventory: '暮らしと生産', industry: '小さな工房を育てる', neighbors: '同じ世界の隣人'}[tab];
  const body = $('panel-content'); body.replaceChildren(); const colony = me();
  if (tab === 'inventory') {
    body.append(el('div', 'section-label', '共有世界から、コアの倉庫へ')); const raw = el('div', 'inventory-list');
    for (const key of catalog.raw) raw.append(resource(key, colony.inventory[key] || 0)); body.append(raw);
    body.append(el('p', 'panel-note', `倉庫は品目ごとに${format(1000000 + (colony.research['6'] || 0) * 500000)}まで。満杯のとき、余分な資源は採らず、加工も入力素材を消費せず待機します。`));
    body.append(el('div', 'section-label', '加工したもの・暮らしの記録')); const products = el('div', 'inventory-list');
    for (const item of catalog.items.filter(i => !catalog.raw.includes(i.key) && (colony.inventory[i.key] || 0) > 0)) products.append(resource(item.key, colony.inventory[item.key]));
    body.append(products.childElementCount ? products : el('p', 'empty', 'まだ加工品がありません。「建てる」から製材所や製粉所を置いてみましょう。'));
    body.append(el('p', 'panel-note', `採集した総量 ${format(colony.gathered)} · コア経験 ${format(colony.experience)} · 隣人との対話 ${format(colony.conversations)}回`));
  } else if (tab === 'industry') {
    const capacity = Math.min(64, 4 + (colony.research['3'] || 0) * 4 + Math.trunc(level(colony) / 10));
    body.append(el('p', 'panel-note', `工房 ${colony.buildings.length}/${capacity}。工房職は住民10人につき2人の役割で誕生します。建設順に人手を割り当てます。`));
    for (const building of colony.buildings) {
      const card = el('div', 'facility-card'), recipe = catalog.recipes[building.recipe], header = el('div', 'card-top');
      header.append(el('h3', '', `${catalog.industries[building.kind].name} #${building.id}`), el('span', 'badge', `${building.health}%`));
      card.append(header, el('p', '', `${itemName(recipe.output)} · ${statusName[building.status] || building.status}`));
      const bar = el('div', 'micro-bar'), fill = el('span'); fill.style.width = `${building.progress / recipe.period * 100}%`; bar.append(fill); card.append(bar);
      card.append(button('この工房を見る', () => { selected = {type: 'building', colonyId: colony.id, id: building.id}; renderSelection(); scene.camera.x = building.x; scene.camera.y = building.y; })); body.append(card);
    }
    body.append(el('div', 'section-label', '新しい施設 · 8種類 / 72のレシピ'));
    for (const facility of catalog.industries) {
      const unlocked = (colony.research[String(facility.branch)] || 0) >= facility.rank;
      const card = el('div', `facility-card${unlocked ? '' : ' locked'}`), top = el('div', 'card-top'), title = el('h3', '', facility.name); title.prepend(el('span', 'facility-mark'));
      top.append(title, el('span', 'badge', unlocked ? '建設可能' : '未研究')); card.append(top);
      card.append(el('p', '', `原木 ${facility.timber} · 石材 ${facility.stone}${unlocked ? '' : ` · ${catalog.branches[facility.branch].name} ${facility.rank}段階が必要`}`));
      const build = button('場所を選んで建てる', () => mode('build', facility.id)); build.disabled = !unlocked || isBusy(); card.append(build); body.append(card);
    }
  } else {
    const neighbors = api.state.world.colonies.filter(c => c.id !== colony.id);
    body.append(el('p', 'panel-note', '近くの住民どうしは自動で対話し、交流の記録と経験を得ます。物資の受け渡しは、送り主のコアから届く範囲で行えます。'));
    if (!neighbors.length) body.append(el('p', 'empty', 'この世界には、まだあなたのコアだけがいます。同じサーバーのURLを友人に伝えると、同じ世界で暮らせます。復帰キーは伝えないでください。'));
    for (const neighbor of neighbors) {
      const card = el('div', 'neighbor-card'), p = position(neighbor, scene.time()), own = position(colony, scene.time());
      card.append(el('h3', '', neighbor.name), el('p', '', `${population(neighbor, api.state.world.tick).count}人 · コア Lv.${level(neighbor)} · 距離 ${format(Math.hypot(p.x - own.x, p.y - own.y))}`));
      const row = el('div', 'button-row'); row.append(button('見に行く', () => { scene.camera.x = p.x; scene.camera.y = p.y; }), button('物資を分ける', () => { giftRecipient = neighbor.id; renderPanel(); })); card.append(row);
      if (giftRecipient === neighbor.id) {
        const form = el('form'), choice = el('select');
        for (const item of catalog.items.filter(i => (colony.inventory[i.key] || 0) > 0)) { const option = el('option', '', `${item.name} (${format(colony.inventory[item.key])})`); option.value = item.key; choice.append(option); }
        choice.setAttribute('aria-label', '送る物資'); const amount = el('input'); amount.type = 'number'; amount.min = '1'; amount.max = '1000000000'; amount.step = '1'; amount.value = '10'; amount.setAttribute('aria-label', '送る数量');
        const presets = el('div', 'button-row'); for (const n of [5, 20, 100]) { const preset = button(String(n), () => { amount.value = String(n); }); preset.type = 'button'; presets.append(preset); }
        const send = el('button', 'primary wide', 'この物資を送る'); send.type = 'submit'; send.disabled = isBusy();
        form.append(choice, amount, presets, send); form.addEventListener('submit', async e => { e.preventDefault(); const value = Number(amount.value); if (!Number.isSafeInteger(value) || value <= 0) return;
          send.disabled = true; await command('transfer', {index: neighbor.id, value, text: choice.value}); giftRecipient = null; renderPanel(); }); card.append(form);
      }
      body.append(card);
    }
  }
}
function renderSelection() {
  if (!selected || !me()) { $('selection').classList.add('hidden'); return; }
  const body = $('selection-body'); body.replaceChildren(); $('selection').classList.remove('hidden');
  if (selected.type === 'node') {
    const node = selected, stored = api.state.world.nodes[node.key], cap = 180 + node.tier * 30;
    const stock = stored ? Math.min(cap, stored.stock + (api.state.world.tick - stored.tick) * (2 + Math.trunc(node.tier / 3))) : cap;
    body.append(el('span', 'eyebrow', 'SHARED DEPOSIT'), el('h2', '', `${itemName(catalog.raw[node.kind])} · 階位 ${node.tier}`),
      el('p', 'numbers', `${format(stock)} / ${format(cap)}`), el('p', '', `全員で使う有限の資源です。10秒に${2 + Math.trunc(node.tier / 3)}再生します。枯渇しても削除されません。`));
    body.append(button('この近くへコアを移動', () => command('move', {x: clamp(Math.round(node.x - 30), -1e6, 1e6), y: clamp(Math.round(node.y + 25), -1e6, 1e6)})));
  } else if (selected.type === 'inhabitant') {
    const colony = colonyById(selected.colonyId); if (!colony) return;
    const age = Math.max(0, api.state.world.tick - selected.birth), generation = Math.floor(age / 360) + 1, lifeAge = age % 360;
    body.append(el('span', 'eyebrow', 'A SMALL LIFE'), el('h2', '', `${inhabitantName(colony, selected.id)} · 第${generation}世代`),
      el('p', '', `${colony.name}の住民 #${selected.id + 1}`), el('p', 'numbers', `Lv.${1 + Math.trunc(lifeAge / 6)} · ${Math.trunc(lifeAge / 6)}分`),
      el('p', '', selected.role < 8 ? `${itemName(catalog.raw[selected.role])}を集める役割です。資源が枯れると、採集を待ちます。` : '工房を動かし、建物を維持する役割です。'),
      el('p', '', `あと約${Math.ceil((360 - lifeAge) / 6)}分でコアへ還り、${6 + (colony.research['6'] || 0) * 2}エッセンスを残します。次の世代は同じ席から生まれます。`));
  } else if (selected.type === 'building') {
    const colony = colonyById(selected.colonyId), building = colony?.buildings.find(b => b.id === selected.id);
    if (!building) { selected = null; $('selection').classList.add('hidden'); return; }
    const recipe = catalog.recipes[building.recipe], output = recipe.amount * (1 + Math.trunc((colony.research[String(recipe.branch)] || 0) / 4));
    body.append(el('span', 'eyebrow', 'AUTONOMOUS WORKSHOP'), el('h2', '', `${catalog.industries[building.kind].name} #${building.id}`),
      el('p', '', `${statusName[building.status] || building.status} · 維持状態 ${building.health}%`),
      el('p', '', `${['a', 'b', 'c'].filter(k => recipe['n' + k] > 0).map(k => `${itemName(recipe[k])} ${recipe['n' + k]}`).join(' ＋ ')} → ${itemName(recipe.output)} ${output}`),
      el('p', '', `${recipe.period * 10}秒 / 人手${recipe.workers} · 累計${format(building.produced)}個を生産`));
    if (colony.id === api.state.me) {
      const choice = el('select'); choice.setAttribute('aria-label', '加工レシピ');
      for (const r of catalog.recipes.filter(r => r.kind === building.kind)) { const option = el('option', '', `${r.tier}. ${itemName(r.output)}${(colony.research[String(r.branch)] || 0) < r.rank ? ' (未研究)' : ''}`);
        option.value = String(r.id); option.disabled = (colony.research[String(r.branch)] || 0) < r.rank; choice.append(option); }
      choice.value = String(building.recipe); choice.disabled = isBusy(); choice.addEventListener('change', () => command('recipe', {index: building.id, value: Number(choice.value)})); body.append(choice);
      const actions = el('div', 'button-row');
      actions.append(button(building.enabled ? '停止する' : '稼働させる', () => command('pause', {index: building.id, value: building.enabled ? 0 : 1})),
        button('修理 (原木5・石5)', () => command('repair', {index: building.id})),
        button('解体', async () => { if (confirm('この工房を解体しますか？ 建設素材の4分の1が戻ります。')) { if (await command('dismantle', {index: building.id})) { selected = null; renderSelection(); } } }));
      for (const b of actions.children) b.disabled = isBusy(); body.append(actions);
    }
    body.append(el('p', 'small', '維持には1分に原木・石材を各1。コアから離れるか素材が切れると傷み、0%で停止します。停止中も維持は必要です。'));
  } else if (selected.type === 'core') {
    const colony = colonyById(selected.colonyId); if (!colony) return;
    const people = population(colony, api.state.world.tick);
    body.append(el('span', 'eyebrow', 'THE HEART OF A COLONY'), el('h2', '', colony.name),
      el('p', 'numbers', `Lv.${format(level(colony))} · ${format(people.count)}人`),
      el('p', '', `採集範囲 ${190 + (colony.research['1'] || 0) * 24} · 世代を越えた${format(colony.deaths)}の命。`));
    if (colony.id === api.state.me) body.append(button('コロニーの名前を変更', async () => { const name = prompt('新しい名前 (1〜32文字)', colony.name); if (name?.trim()) await command('rename', {text: name.trim()}); }));
    else body.append(button('この隣人と物資を分ける', () => { giftRecipient = colony.id; openPanel('neighbors'); }));
  }
}
function pick(hit) {
  if (!entered || !me()) return;
  if (hit.type === 'ground') {
    if (isBusy()) { toast(api.pending ? '未確定の操作を先に再確認してください。' : '世界が現在時刻に追いつくまで計算しています。'); return; }
    const x = clamp(Math.round(hit.x), -1e6, 1e6), y = clamp(Math.round(hit.y), -1e6, 1e6);
    if (scene.mode === 'build' && !hit.move) command('build', {index: scene.buildKind, value: scene.buildKind * 9, x, y}).then(ok => { if (ok) mode('inspect'); });
    else if (scene.mode === 'move' || hit.move) command('move', {x, y}).then(ok => { if (ok) mode('inspect'); });
    else { selected = null; renderSelection(); }
  } else { selected = hit; renderSelection(); }
}
function renderResearch() {
  if (selectedResearch === null || !me()) return;
  const rule = catalog.research[selectedResearch], branch = catalog.branches[rule.branch], colony = me(), rank = colony.research[String(rule.branch)] || 0;
  const body = $('research-detail'); body.replaceChildren(); const stripe = el('div', 'branch-color'); stripe.style.background = branch.color;
  body.append(stripe, el('span', 'eyebrow', `BRANCH ${rule.branch + 1} · STEP ${rule.tier} / 12`), el('h2', '', `${branch.name} ${rule.tier}`), el('p', '', branch.description));
  const effects = [
    `住民の席を48増やします。基本上限は${16 + 48 * rule.tier}人。席を解放したあとの10秒ごとに一人ずつ生まれます。`,
    `採集範囲 ${190 + rule.tier * 24}、移動速度 ${24 + rule.tier * 2}。採れる階位は基礎${1 + rule.tier * 2}＋コア成長分。`,
    `採集職一人あたりの基礎採集量 ${rule.tier + 1}。共有資源の残量と倉庫容量は超えません。`,
    `工房上限の基礎値 ${4 + rule.tier * 4}。工業レシピの段階 ${Math.min(9, rule.tier + 1)}まで。4段階ごとに製品の出来高が増えます。`,
    `製粉所・温室のレシピ ${Math.min(9, rule.tier + 1)}段階まで。4段階ごとに出来高が増えます。`,
    `養殖池のレシピ ${Math.min(9, rule.tier + 1)}段階まで。4段階ごとに出来高が増えます。`,
    `一人の還生で${6 + 2 * rule.tier}エッセンス。倉庫の品目別容量 ${format(1000000 + rule.tier * 500000)}。`,
    `対話の範囲 ${300 + rule.tier * 50}、物資を送れる範囲 ${500 + rule.tier * 100}。対話時のコア経験も増えます。`
  ]; body.append(el('p', '', effects[rule.branch]));
  const costs = [['エッセンス', colony.essence, rule.essence], [itemName(rule.raw), colony.inventory[rule.raw] || 0, rule.raw_amount]];
  if (rule.product_amount) costs.push([itemName(rule.product), colony.inventory[rule.product] || 0, rule.product_amount]);
  for (const [name, have, need] of costs) { const row = el('div', 'cost'); row.append(el('span', '', name), el('span', have >= need ? 'enough' : 'short', `${format(have)} / ${format(need)}`)); body.append(row); }
  const canPay = costs.every(([, have, need]) => have >= need), done = rank >= rule.tier, next = rank + 1 === rule.tier;
  const buy = button(done ? '研究済み' : !next ? 'ひとつ前の研究が必要' : 'この研究を解放する', async () => { buy.disabled = true; await command('research', {index: rule.id}); renderResearch(); }, 'primary wide');
  buy.disabled = done || !next || !canPay || isBusy(); body.append(buy);
  body.append(el('p', 'small', '研究と残した知識は、住民の世代が交代しても失われません。'));
}
async function polling() {
  clearTimeout(pollTimer); if (!entered || document.hidden || pollActive) return;
  pollActive = true;
  try { await api.poll(); }
  catch (error) { $('network').textContent = '再接続中'; $('status-dot').className = 'status-dot offline';
    if (['persistence_shape', 'schema_mismatch', 'unauthorized'].includes(error.code)) toast(errorText(error)); }
  finally { pollActive = false; }
  if (!document.hidden && entered) pollTimer = setTimeout(polling, api.state?.backlog_ticks > 0 ? 100 : 2000);
}
function enter() { entered = true; $('auth').classList.add('hidden'); for (const id of ['colony-hud', 'sidebar', 'toolbar']) $(id).classList.remove('hidden'); scene.center(); onState(api.state); polling(); }
function openKey() { if (!api.token) { toast('コアを作成するか、復帰キーでログインしてください。'); return; } $('key-value').value = api.token; $('key-value').type = 'password'; $('reveal-key').textContent = '表示する'; $('key-dialog').showModal(); }
function downloadKey() {
  if (!api.token) return; const text = `Orbloam recovery key / 復帰キー\n\n${api.token}\n\nコロニー: ${me()?.name || registration?.name || ''}\nサーバー: ${new URL('.', document.baseURI).href}\n\nこのキーを知っている人はコアを操作できます。非公開で保管してください。\nこのファイルはサーバーの保存データではありません。\n`;
  const url = URL.createObjectURL(new Blob([text], {type: 'text/plain;charset=utf-8'})), anchor = el('a'); anchor.href = url; anchor.download = 'orbloam-recovery-key.txt'; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); $('backup-key').classList.add('hidden');
}
function generateSecret() { if (!globalThis.crypto?.getRandomValues) throw new Error('secure_random_unavailable'); const bytes = new Uint8Array(32); crypto.getRandomValues(bytes); return [...bytes].map(b => b.toString(16).padStart(2, '0')).join(''); }
$('join-form').addEventListener('submit', async event => {
  event.preventDefault(); const submit = event.submitter; submit.disabled = true; $('auth-error').textContent = '';
  try {
    const name = $('nickname').value.trim();
    if (!registration) registration = {name, token: generateSecret()};
    api.token = registration.token;
    // Persist before the request: a lost registration reply cannot orphan a saved key.
    if ($('remember').checked) { saveLocal('key', registration.token); saveLocal('registration', JSON.stringify(registration)); }
    else { saveLocal('key', null); saveLocal('registration', null); }
    await api.join(registration.name, registration.token); await api.restore(registration.token); saveLocal('registration', null); registration = null;
    enter(); $('backup-key').classList.remove('hidden');
  } catch (error) { $('auth-error').textContent = error.code ? errorText(error) : '安全な乱数を生成できませんでした。対応するブラウザで開いてください。'; }
  finally { submit.disabled = false; }
});
$('recover-form').addEventListener('submit', async event => {
  event.preventDefault(); const submit = event.submitter; submit.disabled = true; $('auth-error').textContent = '';
  const token = $('recovery-key').value.trim();
  if (!/^[a-f0-9]{64}$/.test(token)) { $('auth-error').textContent = '64文字の復帰キーを、そのまま貼り付けてください。'; submit.disabled = false; return; }
  try { await api.restore(token); saveLocal('key', $('remember').checked ? token : null); saveLocal('registration', null); registration = null; $('recovery-key').value = ''; enter(); }
  catch (error) { $('auth-error').textContent = errorText(error); } finally { submit.disabled = false; }
});
for (const node of document.querySelectorAll('[data-tab]')) node.addEventListener('click', () => openPanel(node.dataset.tab));
for (const node of document.querySelectorAll('[data-close]')) node.addEventListener('click', () => $(node.dataset.close).close());
$('inspect-mode').onclick = () => mode('inspect'); $('move-mode').onclick = () => mode('move'); $('build-mode').onclick = () => openPanel('industry');
$('inventory-button').onclick = () => openPanel('inventory'); $('close-sidebar').onclick = () => $('sidebar').classList.add('hidden');
$('close-selection').onclick = () => { selected = null; renderSelection(); }; $('zoom-in').onclick = () => scene.zoom(1.35); $('zoom-out').onclick = () => scene.zoom(1 / 1.35);
$('center').onclick = $('home-brand').onclick = () => scene.center(); $('help-button').onclick = () => $('help-dialog').showModal();
$('key-button').onclick = openKey; $('save-first-key').onclick = $('download-key').onclick = downloadKey;
$('dismiss-key').onclick = () => $('backup-key').classList.add('hidden');
$('reveal-key').onclick = () => { const hidden = $('key-value').type === 'password'; $('key-value').type = hidden ? 'text' : 'password'; $('reveal-key').textContent = hidden ? '隠す' : '表示する'; };
$('copy-key').onclick = async () => { try { await navigator.clipboard.writeText(api.token); toast('キーをコピーしました。非公開で保管してください。'); }
  catch { $('key-value').type = 'text'; $('key-value').select(); toast('自動コピーが使えません。選択されたキーをコピーしてください。'); } };
$('logout').onclick = () => { if (!confirm('この端末からログアウトしますか？ 戻るには復帰キーが必要です。')) return;
  saveLocal('key', null); saveLocal('registration', null); saveLocal('pending', null); location.reload(); };
$('retry-pending').onclick = async () => { try { await api.retryPending(); toast('操作結果を確認しました。'); } catch (error) { toast(errorText(error)); } };
$('discard-pending').onclick = () => { if (confirm('操作が実行済みか、現在の倉庫やコアの状態を確認しましたか？ 記録を解除しても、その操作を取り消すことにはなりません。')) { api.discardPending(); polling(); } };
$('open-research').onclick = () => { $('research-overlay').classList.remove('hidden'); scene.visible = false; tree.open(); };
$('research-close').onclick = () => { $('research-overlay').classList.add('hidden'); tree.opened = false; scene.visible = true; };
$('research-fit').onclick = () => tree.fit(); $('research-plus').onclick = () => tree.zoom(1.3); $('research-minus').onclick = () => tree.zoom(1 / 1.3);
document.addEventListener('visibilitychange', () => { if (document.hidden) clearTimeout(pollTimer); else polling(); });
document.addEventListener('keydown', event => { if (event.key === 'Escape') { if (tree.opened) $('research-close').click(); else { mode('inspect'); selected = null; renderSelection(); } } });
// Public rendering observations for diagnostics; deliberately no credential or write shortcut.
window.orbloamDiagnostics = () => ({frames: scene.frames, camera: {...scene.camera}, maximumGameRequests: api.maximumInFlight,
  population: me() ? population(me(), api.state.world.tick) : null, backlogTicks: api.state?.backlog_ticks ?? null});
async function boot() {
  try {
    catalog = await api.catalog(); items = new Map(catalog.items.map(item => [item.key, item])); scene.setCatalog(catalog); tree.setCatalog(catalog);
    try { registration = JSON.parse(loadLocal('registration') || 'null'); } catch { saveLocal('registration', null); }
    if (registration) { $('nickname').value = registration.name; $('auth-error').textContent = '前回の登録結果を確認できます。同じ名前・キーで登録を再開します。'; }
    const saved = loadLocal('key'); if (saved && !registration) { try { await api.restore(saved); enter(); } catch (error) { $('auth-error').textContent = errorText(error); } }
  } catch (error) { $('auth-error').textContent = errorText(error); $('network').textContent = '接続できません'; }
}
boot();
