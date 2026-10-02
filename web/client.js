import {GameAPI, errorText, loadLocal, saveLocal} from './api.js';
import {WorldScene, population, position, inhabitantName, clamp, mod, LIFE_TICKS, makeOrb, researchOwned, researchReady, lodForZoom} from './world.js';
import {ResearchTree} from './research.js';

const $ = id => document.getElementById(id);
const el = (tag, className = '', text) => { const node = document.createElement(tag); node.className = className; if (text !== undefined) node.textContent = text; return node; };
const format = n => Math.trunc(n || 0).toLocaleString('en-US');
const show = (id, visible) => $(id).classList.toggle('hidden', !visible);
let catalog, items = new Map(), entered = false, tab = 'overview', selected = null, selectedResearch = null, giftRecipient = null;
let pollTimer, toastTimer, pendingTimer, registration = null, pollActive = false, nextRetry = 0, retryDelay = 1000;
let panelVersion = '', selectionVersion = '', researchVersion = '';
const api = new GameAPI(onState, pendingChanged);
const scene = new WorldScene($('world'), pick);
const tree = new ResearchTree($('research-canvas'), selectResearch);
const me = () => api.state?.world.colonies.find(c => c.id === api.state.me);
const colonyById = id => api.state?.world.colonies.find(c => c.id === id);
const itemName = key => items.get(key)?.name || key.replaceAll('-', ' ');
const busy = () => !!api.pending || api.writeQueued || (api.state?.backlog_ticks || 0) > 0;
const level = colony => 1 + Math.trunc(colony.experience / 250);
const rank = (colony, branch) => colony.research[String(branch)] || 0;
const discovered = colony => Array.from({length: 8}, (_, b) => rank(colony, b)).reduce((a, b) => a + b, 0);
const inputFocused = container => container.contains(document.activeElement) && ['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement.tagName);
const statusName = {working: 'Working', materials: 'Waiting for materials', warehouse: 'Store full', workers: 'Waiting for workers', maintenance: 'Needs repair', distant: 'Beyond the core’s reach', paused: 'Paused'};

function toast(message) { $('toast').textContent = message; show('toast', true); clearTimeout(toastTimer); toastTimer = setTimeout(() => show('toast', false), 4200); }
function button(text, action, className = '') { const node = el('button', className, text); node.type = 'button'; node.addEventListener('click', action); return node; }
function actionButton(text, op, parameters, className = '') { const node = button(text, async () => { node.disabled = true; await command(op, parameters); refresh(true); }, className); node.disabled = busy(); return node; }
function resource(key, amount) { const node = el('div', 'resource'), dot = el('span', 'resource-dot'), body = el('div');
  dot.style.background = items.get(key)?.color || '#abc9b7'; body.append(el('small', '', itemName(key)), el('b', '', format(amount))); node.append(dot, body); return node; }
function labelValue(label, value) { const row = el('div', 'cost'); row.append(el('span', '', label), el('b', '', value)); return row; }
async function command(op, parameters = {}) {
  try { await api.command(op, parameters); return true; }
  catch (error) { if (error.code !== 'pending_action') toast(errorText(error)); return false; }
  finally { refresh(true); }
}
function setMode(mode, kind = 0) {
  scene.mode = mode; scene.buildKind = kind; scene.dirty = true;
  show('mode-hint', mode === 'build'); $('world').style.cursor = mode === 'build' ? 'crosshair' : 'grab';
  if (mode === 'build') $('mode-text').textContent = `Place ${catalog.industries[kind].name} near your core`;
  $('build-mode').classList.toggle('active', mode === 'build');
}
function closeSelection() { selected = scene.selected = null; scene.dirty = true; show('selection', false); }
function openPanel(name) { closeSelection(); setMode('inspect'); tab = name; show('sidebar', true); panelVersion = ''; renderPanel(); }
function closePanels() { show('sidebar', false); closeSelection(); setMode('inspect'); }
function setSelection(hit) { show('sidebar', false); selected = scene.selected = hit; scene.dirty = true; selectionVersion = ''; renderSelection(); }
function connection(online, text) { $('network').textContent = online ? 'Connected' : 'Reconnecting'; $('status-dot').className = `status-dot ${online ? 'online' : 'offline'}`; $('connection').title = text || (online ? `Connected · ${Math.round(api.latency)} ms` : 'Reconnecting safely'); }
function pendingChanged(record) {
  clearTimeout(pendingTimer); if (!record) { show('pending', false); nextRetry = 0; retryDelay = 1000; refresh(true); return; }
  // Ordinary successful commands should not flash an alarming persistent banner.
  pendingTimer = setTimeout(() => { if (api.pending) { renderPending(); show('pending', true); } }, 1400);
}
function renderPending() {
  const conflict = api.pendingError === 'sequence_conflict';
  $('pending-text').textContent = conflict ? 'Another device changed the sequence. Review this action.' : 'Checking the same action automatically…';
  show('discard-pending', conflict); show('retry-pending', conflict);
}
function onState(state) {
  scene.setState(state); const colony = me(); if (!colony) return;
  tree.setColony(colony); $('colony-name').textContent = colony.name;
  const people = population(colony, state.world.tick); $('population').textContent = format(people.count); $('essence').textContent = format(colony.essence);
  $('colony-hud').title = `${colony.name} · ${people.count}/${people.capacity} lives · ${format(colony.essence)} Essence`;
  $('research-progress').textContent = `${discovered(colony)} / 96`; $('research-essence').textContent = `✧ ${format(colony.essence)}`;
  connection(true); show('backlog', state.backlog_ticks > 0); $('backlog-text').textContent = `${format(state.backlog_ticks * 10)} seconds of elapsed life remain`;
  refresh(); viewportChanged();
}
function refresh(force = false) {
  if (!catalog || !me()) return;
  if (force) panelVersion = selectionVersion = researchVersion = '';
  if (!$('sidebar').classList.contains('hidden') && !inputFocused($('panel-content'))) renderPanel();
  if (selected && !inputFocused($('selection-body'))) renderSelection();
  if (tree.opened && selectedResearch !== null) renderResearch();
  if (tree.opened && !$('research-list').classList.contains('hidden')) renderResearchList();
}
function stateVersion(extra = '') { return `${api.state?.world.tick}:${me()?.sequence}:${me()?.essence}:${busy()}:${extra}`; }
function nextReturn(colony) {
  let ticks = LIFE_TICKS;
  for (const cohort of colony.cohorts) {
    const active = clamp(api.state.world.tick - cohort.start + 1, 0, cohort.count);
    // At most one life cycle is needed to find the next cohort return.
    for (let i = 0; i < Math.min(active, LIFE_TICKS); i++) ticks = Math.min(ticks, LIFE_TICKS - mod(api.state.world.tick - cohort.start - i, LIFE_TICKS));
  }
  return ticks * 10;
}
function renderPanel() {
  const colony = me(); if (!catalog || !colony) return;
  const version = stateVersion(tab + ':' + giftRecipient); if (panelVersion === version) return; panelVersion = version;
  for (const node of document.querySelectorAll('[data-tab]')) node.classList.toggle('active', node.dataset.tab === tab);
  $('panel-title').textContent = {overview: colony.name, inventory: 'Stores', industry: 'Workshops', neighbors: 'Neighbors'}[tab];
  const body = $('panel-content'); body.replaceChildren();
  if (tab === 'overview') {
    const p = population(colony, api.state.world.tick), stats = el('div', 'overview-numbers');
    for (const [value, name] of [[format(p.count), 'little lives'], [format(colony.essence), 'Essence'], [format(level(colony)), 'core level']]) { const card = el('div'); card.append(el('b', '', value), el('span', '', name)); stats.append(card); }
    body.append(stats, el('p', 'panel-note', 'Life gathers and creates on its own. There is no daily checklist to keep up with.'));
    body.append(labelValue('Population places', `${p.count} / ${p.capacity}`), labelValue('Next return', `about ${Math.max(1, Math.ceil(nextReturn(colony) / 60))} min`), labelValue('Lifespan', '15 minutes'), labelValue('Lives remembered', format(colony.deaths)), labelValue('Discoveries', `${discovered(colony)} / 96`));
    body.append(el('p', 'small muted', 'Each returning resident leaves Essence. The next generation keeps the same place; your discoveries and workshops remain.'));
    const row = el('div', 'button-row'); row.append(button('Research', openResearch), button('Workshops', () => openPanel('industry'))); body.append(row);
    const details = el('details'); details.append(el('summary', '', 'A few more details'), labelValue('Gathered', format(colony.gathered)), labelValue('Experience', format(colony.experience)), labelValue('Conversations', format(colony.conversations)), labelValue('Gathering radius', format(190 + rank(colony, 1) * 24)));
    details.append(button('Rename colony', async () => { const name = prompt('Colony name (1–32 characters)', colony.name); if (name?.trim()) await command('rename', {text: name.trim()}); })); body.append(details);
  } else if (tab === 'inventory') {
    body.append(el('div', 'section-label', 'GATHERED TOGETHER')); const raw = el('div', 'inventory-list'); for (const key of catalog.raw) raw.append(resource(key, colony.inventory[key] || 0)); body.append(raw);
    body.append(el('div', 'section-label', 'MADE BY LITTLE HANDS')); const products = el('div', 'inventory-list');
    for (const item of catalog.items.filter(i => !catalog.raw.includes(i.key) && (colony.inventory[i.key] || 0) > 0)) products.append(resource(item.key, colony.inventory[item.key]));
    body.append(products.childElementCount ? products : el('p', 'empty', 'Nothing made yet. Place a workshop and your residents will find something useful to make.'));
    body.append(el('p', 'panel-note', `Each item has room for ${format(1000000 + rank(colony, 6) * 500000)}. A full store pauses production without wasting its inputs.`));
  } else if (tab === 'industry') {
    const capacity = Math.min(64, 4 + rank(colony, 3) * 4 + Math.trunc(level(colony) / 10));
    body.append(el('p', 'panel-note', `${colony.buildings.length} / ${capacity} places. Recipes, work, and ordinary maintenance are automatic. Only intervene when you have something particular in mind.`));
    for (const building of colony.buildings) {
      const card = button('', () => { setSelection({type: 'building', colonyId: colony.id, id: building.id}); scene.camera.x = building.x; scene.camera.y = building.y; scene.dirty = true; }, 'facility-card workshop-link');
      const recipe = catalog.recipes[building.recipe], header = el('div', 'card-top'); header.append(el('h3', '', `${catalog.industries[building.kind].name} #${building.id}`), el('span', 'badge', colony.research[`manual:${building.id}`] ? 'Fixed recipe' : 'Automatic'));
      card.append(header, el('p', '', `${itemName(recipe.output)} · ${statusName[building.status] || building.status}`));
      const bar = el('div', 'micro-bar'), fill = el('span'); fill.style.width = `${clamp(building.progress / recipe.period * 100, 0, 100)}%`; bar.append(fill); card.append(bar); body.append(card);
    }
    body.append(el('div', 'section-label', 'GIVE LIFE SOMEWHERE TO CREATE'));
    for (const facility of catalog.industries) {
      const unlocked = rank(colony, facility.branch) >= facility.rank, affordable = (colony.inventory.timber || 0) >= facility.timber && (colony.inventory.stone || 0) >= facility.stone;
      const card = el('div', `facility-card${unlocked ? '' : ' locked'}`), top = el('div', 'card-top'); top.append(el('h3', '', facility.name), el('span', 'badge', unlocked ? 'Ready' : 'Undiscovered')); card.append(top);
      card.append(el('p', '', `Timber ${facility.timber} · Stone ${facility.stone}${unlocked ? '' : ` · ${facility.rank} ${catalog.branches[facility.branch].name} discoveries required`}`));
      const actions = el('div', 'button-row'), build = button('Build nearby', () => buildNearby(facility.id), 'primary'), place = button('Choose a place', () => { closePanels(); setMode('build', facility.id); });
      build.disabled = place.disabled = !unlocked || !affordable || busy() || colony.buildings.length >= capacity; actions.append(build, place); card.append(actions); body.append(card);
    }
  } else {
    const neighbors = api.state.world.colonies.filter(c => c.id !== colony.id);
    body.append(el('p', 'panel-note', 'Residents talk when their colonies are close. Gifts are optional; their lives do not depend on constant visits.'));
    if (!neighbors.length) body.append(el('p', 'empty', 'No other cores yet. Invite someone to this server’s address, never with your recovery key.'));
    for (const neighbor of neighbors) {
      const card = el('div', 'neighbor-card'), p = position(neighbor, scene.time()), own = position(colony, scene.time());
      card.append(el('h3', '', neighbor.name), el('p', '', `${population(neighbor, api.state.world.tick).count} lives · Core level ${level(neighbor)} · ${format(Math.hypot(p.x - own.x, p.y - own.y))} away`));
      const row = el('div', 'button-row'); row.append(button('Visit', () => { closePanels(); scene.camera.x = p.x; scene.camera.y = p.y; scene.dirty = true; }), button('Send a gift', () => { giftRecipient = neighbor.id; panelVersion = ''; renderPanel(); })); card.append(row);
      if (giftRecipient === neighbor.id) {
        const form = el('form'), choice = el('select'), amount = el('input'); choice.setAttribute('aria-label', 'Gift item');
        for (const item of catalog.items.filter(i => (colony.inventory[i.key] || 0) > 0)) { const option = el('option', '', `${item.name} (${format(colony.inventory[item.key])})`); option.value = item.key; choice.append(option); }
        amount.type = 'number'; amount.min = '1'; amount.step = '1'; amount.value = '10'; amount.setAttribute('aria-label', 'Gift amount');
        const send = el('button', 'primary wide', 'Send gift'); send.type = 'submit'; send.disabled = busy() || !choice.options.length;
        form.append(choice, amount, send); form.addEventListener('submit', async event => { event.preventDefault(); const value = Number(amount.value); if (!Number.isSafeInteger(value) || value < 1) return; send.disabled = true;
          if (await command('transfer', {index: neighbor.id, value, text: choice.value})) { giftRecipient = null; panelVersion = ''; renderPanel(); toast('A little gift, delivered.'); } }); card.append(form);
      }
      body.append(card);
    }
  }
}
async function buildNearby(kind) {
  if (busy()) return; const colony = me(), p = position(colony, api.state.now_ms), radius = 190 + rank(colony, 1) * 24;
  // Choose a position, not a reward: native range, cost and spacing checks remain authoritative.
  for (let ring = 55; ring < Math.min(radius - 25, 420); ring += 34) for (let k = 0; k < 16; k++) {
    const angle = k * Math.PI / 8 + .35, x = Math.round(p.x + Math.cos(angle) * ring), y = Math.round(p.y + Math.sin(angle) * ring);
    if (colony.buildings.some(b => Math.hypot(x - b.x, y - b.y) < 30)) continue;
    if (await command('build', {index: kind, value: kind * 9, x, y})) { closePanels(); toast(`${catalog.industries[kind].name} is ready. Your residents will take it from here.`); }
    return;
  }
  toast('No clear space nearby. Choose a place or move your core.');
}
function renderSelection() {
  if (!selected || !me()) { show('selection', false); return; }
  const version = stateVersion(JSON.stringify([selected.type, selected.id, selected.key, selected.colonyId, selected.x, selected.y])); if (version === selectionVersion) return; selectionVersion = version;
  const body = $('selection-body'); body.replaceChildren(); show('selection', true);
  if (selected.type === 'node') {
    const node = selected, stored = api.state.world.nodes[node.key], capacity = 180 + node.tier * 30;
    const stock = stored ? Math.min(capacity, stored.stock + Math.max(0, api.state.world.tick - stored.tick) * (2 + Math.trunc(node.tier / 3))) : capacity;
    body.append(el('span', 'eyebrow', 'A SHARED PLACE'), el('h2', '', itemName(catalog.raw[node.kind])), el('p', 'numbers', `${format(stock)} / ${format(capacity)}`), el('p', '', `Tier ${node.tier} · regrows ${2 + Math.trunc(node.tier / 3)} every 10 seconds. Everyone draws from the same deposit.`));
    body.append(actionButton('Move closer', 'move', {x: clamp(Math.round(node.x - 30), -1e6, 1e6), y: clamp(Math.round(node.y + 25), -1e6, 1e6)}));
  } else if (selected.type === 'region') {
    const old = selected.summary, summary = scene.region(old.cx, old.cy, old.stride);
    body.append(el('span', 'eyebrow', 'THE WIDER LANDSCAPE'), el('h2', '', 'Regional resources'), el('p', '', `${format(summary.counts.reduce((a, b) => a + b, 0))} deposits · tiers ${summary.tierLow}–${summary.tierHigh}`));
    const list = el('div', 'inventory-list'); catalog.raw.forEach((key, k) => list.append(resource(key, summary.stock[k]))); body.append(list, el('p', 'small muted', 'Combined available resources. Every deposit is counted, including depleted ones. The simulation is unchanged.'));
    body.append(button('Look closer', () => { const hit = selected; closeSelection(); scene.camera.x = hit.x; scene.camera.y = hit.y; scene.zoom(Math.min(.8 / scene.camera.zoom, 5)); }));
  } else if (selected.type === 'cluster') {
    body.append(el('span', 'eyebrow', 'A FEW LITTLE WORLDS'), el('h2', '', `${selected.colonies.length} neighboring cores`));
    for (const id of selected.colonies) { const colony = colonyById(id); if (colony) body.append(button(colony.name, () => { const p = position(colony, scene.time()); closeSelection(); scene.camera.x = p.x; scene.camera.y = p.y; scene.zoom(Math.max(1, .8 / scene.camera.zoom)); })); }
  } else if (selected.type === 'inhabitant') {
    const colony = colonyById(selected.colonyId); if (!colony) return;
    const age = Math.max(0, api.state.world.tick - selected.birth), generation = Math.floor(age / LIFE_TICKS) + 1, lifeAge = age % LIFE_TICKS;
    body.append(el('span', 'eyebrow', 'A SMALL LIFE'), el('h2', '', inhabitantName(colony, selected.id)), el('p', '', `Generation ${format(generation)} · ${colony.name}`), el('p', 'numbers', `${Math.floor(lifeAge / 6)} minutes old`));
    body.append(el('p', '', selected.role < 8 ? `Quietly gathering ${itemName(catalog.raw[selected.role]).toLowerCase()}. If the deposit is empty, this resident waits for it to regrow.` : 'Making things and caring for workshops. Work is assigned automatically.'));
    body.append(el('p', 'small muted', `Returns to the core in about ${Math.max(1, Math.ceil((LIFE_TICKS - lifeAge) / 6))} minutes, leaving ${6 + rank(colony, 6) * 2} Essence. Another life then takes this place.`));
  } else if (selected.type === 'building') {
    const colony = colonyById(selected.colonyId), building = colony?.buildings.find(b => b.id === selected.id); if (!building) { closeSelection(); return; }
    const recipe = catalog.recipes[building.recipe], manual = colony.research[`manual:${building.id}`] === 1, output = recipe.amount * (1 + Math.trunc(rank(colony, recipe.branch) / 4));
    body.append(el('span', 'eyebrow', manual ? 'A FIXED RECIPE' : 'AN AUTONOMOUS WORKSHOP'), el('h2', '', `${catalog.industries[building.kind].name} #${building.id}`), el('p', '', `${statusName[building.status] || building.status} · ${building.health}% condition`));
    body.append(el('p', '', `${['a', 'b', 'c'].filter(k => recipe['n' + k] > 0).map(k => `${itemName(recipe[k])} ${recipe['n' + k]}`).join(' + ')} → ${itemName(recipe.output)} ${output}`), el('p', 'small', `${recipe.period * 10} seconds · ${recipe.workers} workers · ${format(building.produced)} made`));
    if (colony.id === api.state.me) {
      body.append(el('p', 'panel-note', manual ? 'This workshop keeps your chosen recipe until you return it to automatic.' : 'Chooses an unlocked recipe with enough materials and space, favoring products with lower stock. Finishes work already in progress.'));
      if (manual) body.append(actionButton('Let residents choose', 'auto', {index: building.id}, 'primary wide'));
      const details = el('details'); details.append(el('summary', '', 'Take a little more control'));
      const choice = el('select'); choice.setAttribute('aria-label', 'Fixed workshop recipe');
      for (const r of catalog.recipes.filter(r => r.kind === building.kind)) { const unlocked = rank(colony, r.branch) >= r.rank, option = el('option', '', `${itemName(r.output)}${unlocked ? '' : ' · undiscovered'}`); option.value = String(r.id); option.disabled = !unlocked; choice.append(option); }
      choice.value = String(building.recipe); choice.disabled = busy();
      const fix = button('Use this fixed recipe', () => command('recipe', {index: building.id, value: Number(choice.value)})); fix.disabled = busy(); details.append(choice, fix);
      const controls = el('div', 'button-row'); controls.append(actionButton(building.enabled ? 'Pause' : 'Resume', 'pause', {index: building.id, value: building.enabled ? 0 : 1}), actionButton('Repair now · 5 timber + 5 stone', 'repair', {index: building.id}));
      const dismantle = button('Dismantle', async () => { if (confirm('Dismantle this workshop? One quarter of its construction materials will be returned.')) if (await command('dismantle', {index: building.id})) closeSelection(); }, 'quiet'); dismantle.disabled = busy(); controls.append(dismantle); details.append(controls); body.append(details);
    }
    body.append(el('p', 'small muted', 'Ordinary upkeep is automatic: 1 timber and 1 stone per minute while close to the core. Distance or shortages can cause damage. Pausing production does not remove upkeep.'));
  } else if (selected.type === 'core') {
    const colony = colonyById(selected.colonyId); if (!colony) return; const p = population(colony, api.state.world.tick);
    body.append(el('span', 'eyebrow', 'THE HEART OF A LITTLE WORLD'), el('h2', '', colony.name), el('p', 'numbers', `Level ${format(level(colony))} · ${format(p.count)} lives`), el('p', '', `${format(colony.deaths)} lives remembered. ${discovered(colony)} discoveries carried forward.`));
    body.append(button(colony.id === api.state.me ? 'Open colony' : 'Visit neighbors', () => { if (colony.id !== api.state.me) giftRecipient = colony.id; openPanel(colony.id === api.state.me ? 'overview' : 'neighbors'); }));
  }
}
function pick(hit) {
  if (!entered || !me()) return;
  if (hit.type !== 'ground') { setSelection(hit); return; }
  if (busy()) { if (api.state?.backlog_ticks > 0) toast('Life is catching up. Your core will be ready shortly.'); return; }
  const x = clamp(Math.round(hit.x), -1e6, 1e6), y = clamp(Math.round(hit.y), -1e6, 1e6);
  if (scene.mode === 'build' && !hit.move) command('build', {index: scene.buildKind, value: scene.buildKind * 9, x, y}).then(ok => { if (ok) { setMode('inspect'); toast('Your residents will take it from here.'); } });
  else { closePanels(); command('move', {x, y}); }
}
function selectResearch(id) { selectedResearch = id; tree.selected = id; show('research-list', false); researchVersion = ''; renderResearch(); tree.focus(id); }
function openResearch() { if (!entered) return; closePanels(); show('hover-label', false); show('research-overlay', true); scene.visible = false; tree.open(); $('research-close').focus(); refresh(true); }
function closeResearch() { show('research-overlay', false); tree.opened = false; scene.visible = true; scene.dirty = true; $('open-research').focus(); }
function renderResearch() {
  if (selectedResearch === null || !me()) return;
  const version = stateVersion(String(selectedResearch)); if (version === researchVersion) return; researchVersion = version;
  const rule = catalog.research[selectedResearch], branch = catalog.branches[rule.branch], colony = me(), owned = researchOwned(colony.research, rule), ready = researchReady(colony.research, rule, catalog);
  const body = $('research-detail'); body.replaceChildren(); show('research-detail', true);
  const close = button('×', () => { selectedResearch = tree.selected = null; show('research-detail', false); tree.draw(); }, 'icon close'); close.setAttribute('aria-label', 'Close discovery details');
  const stripe = el('div', 'branch-color'); stripe.style.background = branch.color;
  body.append(close, stripe, el('span', 'eyebrow', `${branch.name.toUpperCase()} · DISCOVERY ${rule.tier}`), el('h2', '', rule.name), el('p', '', branch.description));
  const effects = ['Adds 48 places for new residents. One new resident arrives per 10-second step.', 'Extends gathering reach by 24 and increases core movement speed and accessible deposit tiers.', 'Adds one to each gatherer’s base yield, within the shared deposit and store limits.', 'Adds four workshop places and unlocks higher industrial recipes. Every fourth family discovery increases batch output.', 'Unlocks higher Mill and Greenhouse recipes. Every fourth family discovery increases batch output.', 'Unlocks higher Hatchery recipes. Every fourth family discovery increases batch output.', 'Adds 2 Essence per returning resident and 500,000 storage per item.', 'Extends conversation and gift ranges, and increases experience from conversations.'];
  body.append(el('p', '', effects[rule.branch]));
  if (rule.parent >= 0) { const parent = catalog.research[rule.parent], link = button(`From ${parent.name} ↗`, () => selectResearch(parent.id), 'parent-link'); body.append(link); }
  if (!owned) {
    const costs = [['Essence', colony.essence, rule.essence], [itemName(rule.raw), colony.inventory[rule.raw] || 0, rule.raw_amount]];
    if (rule.product_amount) costs.push([itemName(rule.product), colony.inventory[rule.product] || 0, rule.product_amount]);
    for (const [name, have, need] of costs) { const row = el('div', 'cost'); row.append(el('span', '', name), el('span', have >= need ? 'enough' : 'short', `${format(have)} / ${format(need)}`)); body.append(row); }
    const canPay = costs.every(([, have, need]) => have >= need), buy = button(!ready ? 'Discover the connected parent first' : !canPay ? 'Gather a little more' : 'Make this discovery', async () => { buy.disabled = true; if (await command('research', {index: rule.id})) toast(`${rule.name}, remembered.`); refresh(true); }, 'primary wide');
    buy.disabled = !ready || !canPay || busy(); body.append(buy);
  } else body.append(el('p', 'owned-note', '✓ This discovery belongs to your colony.'));
  const children = catalog.research.filter(n => n.parent === rule.id); if (children.length) { const next = el('div', 'button-row'); for (const child of children) next.append(button(child.name + ' ↗', () => selectResearch(child.id))); body.append(el('div', 'section-label', 'WHERE THIS PATH CAN LEAD'), next); }
  body.append(el('p', 'small muted', 'Choose either branch. Sibling discoveries do not have to be bought in order.'));
}
function renderResearchList() {
  const body = $('research-list'); if (inputFocused(body)) return; const scroll = body.scrollTop; body.replaceChildren();
  const close = button('×', () => show('research-list', false), 'icon close'); close.setAttribute('aria-label', 'Close discovery list'); body.append(close, el('h2', '', 'Choose a direction'));
  for (const branch of catalog.branches) { body.append(el('div', 'section-label', branch.name));
    for (const node of catalog.research.filter(n => n.branch === branch.id)) {
      const owned = researchOwned(me().research, node), ready = researchReady(me().research, node, catalog);
      const b = button(`${owned ? '✓' : ready ? '✧' : '·'} ${node.name}`, () => selectResearch(node.id), 'research-list-item'); b.title = node.parent < 0 ? 'Starts at your core' : `Requires ${catalog.research[node.parent].name}`; body.append(b);
    }
  }
  body.scrollTop = scroll;
}
function viewportChanged() {
  const z = scene.camera.zoom; $('zoom-label').textContent = `${Math.round(z * 100)}%`;
  const desired = 64 / z, magnitude = 10 ** Math.floor(Math.log10(desired)), units = [1, 2, 5, 10].find(n => n * magnitude >= desired) * magnitude;
  $('scale-line').style.width = `${units * z}px`; $('scale-label').textContent = format(units); $('survey').textContent = lodForZoom(z).name;
}
scene.onViewport = viewportChanged;
scene.onHover = (hit, x, y) => {
  if (!entered || tree.opened || scene.mode === 'build' || !hit || ['region', 'ground'].includes(hit.type)) { show('hover-label', false); return; }
  const text = hit.type === 'node' ? itemName(catalog.raw[hit.kind]) : hit.type === 'core' ? colonyById(hit.colonyId)?.name : hit.type === 'building' ? catalog.industries[colonyById(hit.colonyId)?.buildings.find(b => b.id === hit.id)?.kind]?.name : hit.type === 'inhabitant' ? inhabitantName(colonyById(hit.colonyId), hit.id) : `${hit.colonies?.length || 0} cores`;
  $('hover-label').textContent = text || ''; $('hover-label').style.left = `${clamp(x + 14, 8, innerWidth - 180)}px`; $('hover-label').style.top = `${clamp(y - 28, 8, innerHeight - 40)}px`; show('hover-label', !!text);
};
async function polling() {
  clearTimeout(pollTimer); if (!entered || document.hidden || pollActive) return; pollActive = true;
  try {
    await api.poll();
    if (api.pending && api.pendingError !== 'sequence_conflict' && performance.now() >= nextRetry && !api.writeQueued) {
      try { await api.retryPending(); }
      catch (error) { nextRetry = performance.now() + retryDelay; retryDelay = Math.min(15000, retryDelay * 2); renderPending(); if (error.code === 'sequence_conflict') show('pending', true); }
    }
  } catch (error) { connection(false); if (['persistence_shape', 'schema_mismatch', 'unauthorized'].includes(error.code)) { entered = false; toast(errorText(error)); show('auth', true); $('auth-error').textContent = errorText(error); } }
  finally { pollActive = false; }
  if (!document.hidden && entered) pollTimer = setTimeout(polling, api.state?.backlog_ticks > 0 ? 160 : 1200);
}
function enter() { entered = true; show('auth', false); for (const id of ['colony-hud', 'toolbar', 'camera-tools']) show(id, true); closePanels(); scene.center(); onState(api.state); polling(); }
function openKey() { $('menu-dialog').close(); if (!api.token || !entered) { toast('Begin or return to your colony first.'); return; } $('key-value').value = api.token; $('key-value').type = 'password'; $('reveal-key').textContent = 'Reveal'; $('key-dialog').showModal(); }
function downloadKey() {
  if (!api.token) return;
  const text = `Orbloam recovery key\n\n${api.token}\n\nColony: ${me()?.name || registration?.name || ''}\nServer: ${new URL('.', document.baseURI).href}\n\nKeep this private: anyone with this key can control your core.\nThis is not a backup of the server's world data.\n`;
  const url = URL.createObjectURL(new Blob([text], {type: 'text/plain;charset=utf-8'})), anchor = el('a'); anchor.href = url; anchor.download = 'orbloam-recovery-key.txt'; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); show('backup-key', false);
}
function generateSecret() { if (!globalThis.crypto?.getRandomValues) throw new Error('secure_random_unavailable'); const bytes = new Uint8Array(32); crypto.getRandomValues(bytes); return [...bytes].map(b => b.toString(16).padStart(2, '0')).join(''); }
$('join-form').addEventListener('submit', async event => {
  event.preventDefault(); const submit = event.submitter || $('join-form').querySelector('button'); submit.disabled = true; $('auth-error').textContent = '';
  try {
    const name = $('nickname').value.trim(); if (!registration) registration = {name, token: generateSecret()}; api.token = registration.token;
    // Persist before transmission so a lost registration reply is recoverable.
    if ($('remember').checked) { saveLocal('key', registration.token); saveLocal('registration', JSON.stringify(registration)); }
    else { saveLocal('key', null); saveLocal('registration', null); }
    await api.join(registration.name, registration.token); await api.restore(registration.token); saveLocal('registration', null); registration = null; enter(); show('backup-key', true);
  } catch (error) { $('auth-error').textContent = error.code ? errorText(error) : 'Secure random keys are unavailable. Open this in a supported browser.'; }
  finally { submit.disabled = false; }
});
$('recover-form').addEventListener('submit', async event => {
  event.preventDefault(); const submit = event.submitter || $('recover-form').querySelector('button'); submit.disabled = true; $('auth-error').textContent = ''; const token = $('recovery-key').value.trim();
  if (!/^[a-f0-9]{64}$/.test(token)) { $('auth-error').textContent = 'Paste the original 64-character recovery key.'; submit.disabled = false; return; }
  try { await api.restore(token); saveLocal('key', $('remember').checked ? token : null); saveLocal('registration', null); registration = null; $('recovery-key').value = ''; enter(); }
  catch (error) { $('auth-error').textContent = errorText(error); } finally { submit.disabled = false; }
});
for (const node of document.querySelectorAll('[data-tab]')) node.addEventListener('click', () => openPanel(node.dataset.tab));
for (const node of document.querySelectorAll('[data-close]')) node.addEventListener('click', () => $(node.dataset.close).close());
$('build-mode').onclick = () => openPanel('industry'); $('inventory-button').onclick = $('colony-hud').onclick = () => $('sidebar').classList.contains('hidden') ? openPanel('overview') : show('sidebar', false);
$('close-sidebar').onclick = () => show('sidebar', false); $('close-selection').onclick = closeSelection; $('cancel-mode').onclick = () => setMode('inspect');
$('zoom-in').onclick = () => scene.zoom(1.4); $('zoom-out').onclick = () => scene.zoom(1 / 1.4); $('center').onclick = $('home-brand').onclick = () => { scene.center(); if (scene.camera.zoom < .5) scene.zoom(1 / scene.camera.zoom); viewportChanged(); };
$('menu-button').onclick = () => $('menu-dialog').showModal(); $('help-button').onclick = () => { $('menu-dialog').close(); $('help-dialog').showModal(); };
$('key-button').onclick = openKey; $('save-first-key').onclick = $('download-key').onclick = downloadKey; $('dismiss-key').onclick = () => show('backup-key', false);
$('reveal-key').onclick = () => { const hidden = $('key-value').type === 'password'; $('key-value').type = hidden ? 'text' : 'password'; $('reveal-key').textContent = hidden ? 'Hide' : 'Reveal'; };
$('key-dialog').addEventListener('close', () => { $('key-value').value = ''; });
$('copy-key').onclick = async () => { try { await navigator.clipboard.writeText(api.token); toast('Recovery key copied. Keep it private.'); } catch { $('key-value').type = 'text'; $('key-value').select(); toast('Copy the selected key manually.'); } };
$('logout').onclick = () => { if (!confirm('Sign out of this browser? You need your recovery key to return. Any uncertain action should be resolved first.')) return;
  if (api.pending) { toast('Resolve the pending action before signing out.'); return; } saveLocal('key', null); saveLocal('registration', null); saveLocal('pending', null); location.reload(); };
$('retry-pending').onclick = async () => { try { await api.retryPending(); } catch (error) { toast(errorText(error)); } };
$('discard-pending').onclick = () => { if (confirm('Have you checked whether this action already happened? Clearing this record will NOT undo it.')) { api.discardPending(); polling(); } };
function cinematic() { const hidden = document.body.classList.toggle('cinema'); show('restore-ui', hidden); show('hover-label', false); $('menu-dialog').close(); }
$('hide-ui').onclick = $('restore-ui').onclick = cinematic;
$('open-research').onclick = openResearch; $('research-close').onclick = closeResearch;
$('research-fit').onclick = () => { selectedResearch = tree.selected = null; show('research-detail', false); show('research-list', false); tree.fit(); };
$('research-plus').onclick = () => tree.zoom(1.3); $('research-minus').onclick = () => tree.zoom(1 / 1.3);
$('research-list-toggle').onclick = () => { const open = $('research-list').classList.contains('hidden'); show('research-list', open); if (open) { show('research-detail', false); renderResearchList(); } };
document.addEventListener('visibilitychange', () => { if (document.hidden) clearTimeout(pollTimer); else { scene.dirty = true; polling(); } });
document.addEventListener('keydown', event => {
  if (['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement.tagName) || document.querySelector('dialog[open]')) return;
  if (event.key === 'Escape') { if (tree.opened) { if (!$('research-detail').classList.contains('hidden')) { selectedResearch = tree.selected = null; show('research-detail', false); tree.draw(); } else closeResearch(); } else closePanels(); }
  else if (event.key.toLowerCase() === 'h' && entered) cinematic();
  else if (event.key === 'Home' && entered) { event.preventDefault(); $('center').click(); }
  else if (event.key.toLowerCase() === 'r' && entered) tree.opened ? closeResearch() : openResearch();
  else if (event.key.toLowerCase() === 'b' && entered && !tree.opened) openPanel('industry');
  else if (['+', '=', '-'].includes(event.key)) (tree.opened ? tree : scene).zoom(event.key === '-' ? 1 / 1.3 : 1.3);
});
// Rendering diagnostics contain no credentials and no write shortcuts.
window.orbloamDiagnostics = () => ({frames: scene.frames, camera: {...scene.camera}, rendering: {...scene.metrics}, maximumGameRequests: api.maximumInFlight,
  population: me() ? population(me(), api.state.world.tick) : null, backlogTicks: api.state?.backlog_ticks ?? null,
  selected: selected?.type || null, researchNodes: tree.nodes.map(n => ({id:n.id,parent:n.parent,x:n.x,y:n.y,depth:n.depth})),
  researchCamera: {...tree.camera}, researchLabels: tree.labels || [], pendingAction: !!api.pending, sidebarOpen: !$('sidebar').classList.contains('hidden')});
const authContext = $('auth-orb').getContext('2d'); authContext.drawImage(makeOrb(), 24, 24, 208, 208);
viewportChanged();
async function boot() {
  try {
    catalog = await api.catalog(); if (catalog.version < 2 || catalog.lifespan_ticks !== LIFE_TICKS) throw {code: 'invalid_response', status: 502};
    items = new Map(catalog.items.map(item => [item.key, item])); scene.setCatalog(catalog); tree.setCatalog(catalog);
    try { registration = JSON.parse(loadLocal('registration') || 'null'); if (registration && (!/^[a-f0-9]{64}$/.test(registration.token) || typeof registration.name !== 'string')) registration = null; } catch { saveLocal('registration', null); }
    if (registration) { $('nickname').value = registration.name; $('auth-error').textContent = 'Resume the previous registration with its original name and key.'; }
    const saved = loadLocal('key'); if (saved && !registration) { try { await api.restore(saved); enter(); } catch (error) { $('auth-error').textContent = errorText(error); } }
  } catch (error) { $('auth-error').textContent = errorText(error); connection(false); }
}
boot();
