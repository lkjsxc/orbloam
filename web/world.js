// Rendering only. Currency, births, work allocation and orders remain server-owned.
export const mod = (x, n) => ((x % n) + n) % n;
export const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));
export function population(colony, tick) {
  let count = 0, capacity = 0;
  for (const cohort of colony.cohorts) {
    capacity += cohort.count;
    count += clamp(tick - cohort.start + 1, 0, cohort.count);
  }
  return {count, capacity};
}
export function position(colony, ms) {
  const elapsed = clamp(ms - colony.move_at, 0, colony.move_ms);
  return {x: colony.from_x + Math.trunc((colony.to_x - colony.from_x) * elapsed / Math.max(1, colony.move_ms)),
          y: colony.from_y + Math.trunc((colony.to_y - colony.from_y) * elapsed / Math.max(1, colony.move_ms))};
}
export function nodeAt(cx, cy) {
  const salt = mod(cx * 92821 + cy * 68917 + 19139, 2147483647);
  return {x: cx * 128 + 24 + mod(salt, 80), y: cy * 128 + 24 + mod(Math.trunc(salt / 97), 80),
          kind: mod(cx + 3 * cy, 8), tier: 1 + Math.trunc(Math.max(Math.abs(cx), Math.abs(cy)) / 8), key: `${cx}:${cy}`};
}
const names = ['アオ', 'ミオ', 'ナギ', 'ユウ', 'ハル', 'リオ', 'スイ', 'ノア', 'トワ', 'コハク', 'ソラ', 'ユキ', 'リン', 'カイ', 'ヒナ', 'ルカ'];
export function inhabitantName(colony, id) { return names[mod(id * 7 + colony.id * 3, names.length)]; }
export class WorldScene {
  constructor(canvas, onPick) {
    this.canvas = canvas; this.ctx = canvas.getContext('2d', {alpha: false});
    this.staticLayer = document.createElement('canvas'); this.staticCtx = this.staticLayer.getContext('2d', {alpha: false});
    this.camera = {x: -100, y: 0, zoom: 1}; this.state = null; this.catalog = null;
    this.onPick = onPick; this.staticKey = ''; this.staticHits = []; this.hits = []; this.pointers = new Map();
    this.mode = 'inspect'; this.buildKind = 0; this.cursor = null; this.selected = null; this.visible = true;
    this.frames = 0; this.lastDraw = 0; this.lastSeen = performance.now(); this.reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
    this.resize(); window.addEventListener('resize', () => this.resize());
    this.bindInput(); this.loop = this.loop.bind(this); requestAnimationFrame(this.loop);
  }
  resize() {
    this.width = window.innerWidth; this.height = window.innerHeight; this.dpr = Math.min(2, window.devicePixelRatio || 1);
    this.canvas.width = this.staticLayer.width = Math.round(this.width * this.dpr);
    this.canvas.height = this.staticLayer.height = Math.round(this.height * this.dpr); this.staticKey = '';
  }
  setCatalog(catalog) { this.catalog = catalog; this.staticKey = ''; }
  setState(state) { this.state = state; this.lastSeen = performance.now(); }
  get me() { return this.state?.world.colonies.find(c => c.id === this.state.me); }
  time() {
    if (!this.state) return Date.now();
    if (this.state.backlog_ticks > 0) return this.state.world.tick * 10000;
    return this.state.now_ms + Math.min(2200, performance.now() - this.lastSeen);
  }
  center() { if (this.me) { const p = position(this.me, this.time()); this.camera.x = p.x; this.camera.y = p.y; this.staticKey = ''; } }
  zoom(factor, sx = this.width / 2, sy = this.height / 2) {
    const before = this.toWorld(sx, sy); this.camera.zoom = clamp(this.camera.zoom * factor, .025, 4);
    const after = this.toWorld(sx, sy); this.camera.x = clamp(this.camera.x + before.x - after.x, -1e6, 1e6);
    this.camera.y = clamp(this.camera.y + before.y - after.y, -1e6, 1e6); this.staticKey = '';
    document.getElementById('zoom-label').textContent = `${Math.round(this.camera.zoom * 100)}%`;
  }
  toWorld(x, y) { return {x: this.camera.x + (x - this.width / 2) / this.camera.zoom, y: this.camera.y + (y - this.height / 2) / this.camera.zoom}; }
  bindInput() {
    const canvas = this.canvas;
    canvas.addEventListener('wheel', e => { e.preventDefault(); this.zoom(Math.exp(-clamp(e.deltaY, -180, 180) * .002), e.clientX, e.clientY); }, {passive: false});
    canvas.addEventListener('pointerdown', e => {
      if (e.button !== 0) return;
      this.pointers.set(e.pointerId, {x: e.clientX, y: e.clientY}); canvas.setPointerCapture(e.pointerId);
      this.drag = {x: e.clientX, y: e.clientY, cx: this.camera.x, cy: this.camera.y, moved: false};
      if (this.pointers.size === 2) { const [p, q] = [...this.pointers.values()]; this.pinch = Math.hypot(p.x - q.x, p.y - q.y); this.drag.moved = true; }
    });
    canvas.addEventListener('pointermove', e => {
      this.cursor = this.toWorld(e.clientX, e.clientY);
      document.getElementById('coordinates').textContent = `${Math.round(this.cursor.x).toLocaleString()}, ${Math.round(this.cursor.y).toLocaleString()}`;
      if (!this.pointers.has(e.pointerId)) return;
      this.pointers.set(e.pointerId, {x: e.clientX, y: e.clientY});
      if (this.pointers.size === 2) { const [p, q] = [...this.pointers.values()], distance = Math.hypot(p.x - q.x, p.y - q.y);
        if (this.pinch > 0) this.zoom(distance / this.pinch, (p.x + q.x) / 2, (p.y + q.y) / 2); this.pinch = distance; this.drag.moved = true; return; }
      if (!this.drag) return;
      const dx = e.clientX - this.drag.x, dy = e.clientY - this.drag.y;
      if (Math.hypot(dx, dy) > 5) this.drag.moved = true;
      if (this.drag.moved) { this.camera.x = clamp(this.drag.cx - dx / this.camera.zoom, -1e6, 1e6); this.camera.y = clamp(this.drag.cy - dy / this.camera.zoom, -1e6, 1e6); this.staticKey = ''; }
    });
    canvas.addEventListener('pointerup', e => {
      const moved = this.drag?.moved; this.pointers.delete(e.pointerId);
      if (this.pointers.size) { this.drag = null; return; }
      this.drag = null; this.pinch = 0;
      if (!moved && e.button === 0) { const p = this.toWorld(e.clientX, e.clientY); this.onPick(this.mode === 'inspect' ? this.pick(p) : {type: 'ground', ...p}); }
    });
    canvas.addEventListener('pointercancel', () => { this.pointers.clear(); this.drag = null; });
    canvas.addEventListener('contextmenu', e => { e.preventDefault(); this.onPick({type: 'ground', ...this.toWorld(e.clientX, e.clientY), move: true}); });
  }
  pick(point) {
    const priority = {core: 0, building: 1, inhabitant: 2, node: 3};
    let best = null, score = Infinity;
    for (const hit of this.hits) {
      const distance = Math.hypot(point.x - hit.x, point.y - hit.y);
      if (distance > Math.max(hit.radius, 7 / this.camera.zoom)) continue;
      const value = priority[hit.type] * 10000 + distance;
      if (value < score) { score = value; best = hit; }
    }
    return best || {type: 'ground', ...point};
  }
  transform(ctx) { const z = this.camera.zoom; ctx.setTransform(this.dpr * z, 0, 0, this.dpr * z, this.dpr * (this.width / 2 - this.camera.x * z), this.dpr * (this.height / 2 - this.camera.y * z)); }
  bounds(margin = 0) { return {left: this.camera.x - this.width / this.camera.zoom / 2 - margin, right: this.camera.x + this.width / this.camera.zoom / 2 + margin,
    top: this.camera.y - this.height / this.camera.zoom / 2 - margin, bottom: this.camera.y + this.height / this.camera.zoom / 2 + margin}; }
  circle(ctx, x, y, r, fill, stroke, width = 1) { ctx.beginPath(); ctx.arc(x, y, Math.max(.01, r), 0, Math.PI * 2); if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = width; ctx.stroke(); } }
  staticWorld() {
    const z = this.camera.zoom, tick = this.state?.world.tick ?? 0;
    const key = `${this.width}:${this.height}:${this.camera.x}:${this.camera.y}:${z}:${tick}`;
    if (key === this.staticKey) return; this.staticKey = key;
    const ctx = this.staticCtx; ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.fillStyle = '#10171c'; ctx.fillRect(0, 0, this.staticLayer.width, this.staticLayer.height);
    this.transform(ctx); const bounds = this.bounds(180); this.staticHits = [];
    const stride = Math.max(1, 2 ** Math.max(0, Math.ceil(Math.log2(.45 / z))));
    const grid = 128 * stride; ctx.lineWidth = .7 / z;
    for (let x = Math.floor(bounds.left / grid) * grid; x < bounds.right; x += grid) {
      ctx.strokeStyle = mod(Math.round(x / grid), 4) === 0 ? '#29373d' : '#202c32'; ctx.beginPath(); ctx.moveTo(x, bounds.top); ctx.lineTo(x, bounds.bottom); ctx.stroke();
    }
    for (let y = Math.floor(bounds.top / grid) * grid; y < bounds.bottom; y += grid) {
      ctx.strokeStyle = mod(Math.round(y / grid), 4) === 0 ? '#29373d' : '#202c32'; ctx.beginPath(); ctx.moveTo(bounds.left, y); ctx.lineTo(bounds.right, y); ctx.stroke();
    }
    if (!this.catalog) return;
    for (let cx = Math.floor(bounds.left / grid) * stride; cx <= Math.ceil(bounds.right / 128); cx += stride) {
      for (let cy = Math.floor(bounds.top / grid) * stride; cy <= Math.ceil(bounds.bottom / 128); cy += stride) {
        const node = nodeAt(cx, cy), stored = this.state?.world.nodes[node.key];
        const capacity = 180 + node.tier * 30, stock = stored ? Math.min(capacity, stored.stock + (tick - stored.tick) * (2 + Math.trunc(node.tier / 3))) : capacity;
        const color = this.catalog.items[node.kind].color, radius = clamp(9 + Math.log2(node.tier + 1) * 2, 9, 21);
        const alpha = clamp(stock / capacity, 0, 1);
        this.circle(ctx, node.x, node.y, Math.max(radius, 2 / z), color + (alpha > .1 ? '20' : '06'), color + (alpha > .1 ? '66' : '22'), 1 / z);
        this.circle(ctx, node.x, node.y, Math.max(2, radius * .55 * Math.sqrt(alpha)), color + (alpha > .1 ? '77' : '11'));
        if (z > .8 && node.tier > 1) { ctx.font = `${9 / z}px system-ui`; ctx.textAlign = 'center'; ctx.fillStyle = '#8aa29d'; ctx.fillText(`T${node.tier}`, node.x, node.y + radius + 12 / z); }
        if (stride === 1) this.staticHits.push({type: 'node', ...node, stock, capacity, radius});
      }
    }
    this.survey = stride > 1;
  }
  draw() {
    this.staticWorld(); const ctx = this.ctx, z = this.camera.zoom;
    ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.drawImage(this.staticLayer, 0, 0); this.transform(ctx);
    this.hits = this.staticHits.slice(); if (!this.state || !this.catalog) return;
    const ms = this.time(), tick = this.state.world.tick, bounds = this.bounds(600); let aggregated = this.survey;
    for (const colony of this.state.world.colonies) {
      if (colony.created_tick > tick) continue;
      const point = position(colony, ms), own = colony.id === this.state.me;
      const color = own ? '#afe0c5' : this.catalog.branches[mod(colony.id + 2, 8)].color;
      const radius = 190 + (colony.research['1'] || 0) * 24;
      for (const building of colony.buildings) {
        if (building.x < bounds.left || building.x > bounds.right || building.y < bounds.top || building.y > bounds.bottom) continue;
        const active = building.status === 'working', r = 17;
        this.circle(ctx, building.x, building.y, r, active ? color + '25' : '#273037', color + (building.health > 0 ? 'aa' : '33'), 1.3 / z);
        this.circle(ctx, building.x, building.y, r + 4, null, '#a8c7b922', 1 / z);
        if (z > .4) { ctx.fillStyle = color; ctx.font = `${10 / z}px system-ui`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(['製', '窯', '精', '織', '粉', '温', '養', '機'][building.kind], building.x, building.y); ctx.textBaseline = 'alphabetic'; }
        if (active && z > .4) { const recipe = this.catalog.recipes[building.recipe]; ctx.beginPath(); ctx.arc(building.x, building.y, r + 4, -Math.PI / 2, -Math.PI / 2 + 2 * Math.PI * building.progress / recipe.period); ctx.strokeStyle = color; ctx.lineWidth = 1.5 / z; ctx.stroke(); }
        this.hits.push({type: 'building', x: building.x, y: building.y, radius: r, colonyId: colony.id, id: building.id});
      }
      if (point.x < bounds.left || point.x > bounds.right || point.y < bounds.top || point.y > bounds.bottom) continue;
      if (own && z > .12) this.circle(ctx, point.x, point.y, radius, '#80bba004', '#89b5a71c', 1 / z);
      const {count} = population(colony, tick), stride = z < .17 ? Math.max(8, Math.ceil(count / 30)) : z < .4 ? 3 : Math.max(1, Math.ceil(count / 1800));
      if (stride > 1 && count > 0) aggregated = true;
      const routes = new Map(colony.routes.map(r => [r.job, r]));
      for (const cohort of colony.cohorts) {
        const active = clamp(tick - cohort.start + 1, 0, cohort.count);
        for (let i = 0; i < active; i++) {
          const id = cohort.first + i; if (id % stride) continue;
          const role = id % 10, birth = cohort.start + i, age = Math.max(0, ms / 10000 - birth), generation = Math.floor(age / 360);
          const phase = this.reduced ? .42 : mod(ms / 10000 + id * .137, 1), travel = phase < .5 ? phase * 2 : 2 - phase * 2;
          const angle = id * 2.39996 + colony.id, orbit = 20 + (id % 13) * 2;
          let x = point.x + Math.cos(angle) * orbit, y = point.y + Math.sin(angle) * orbit;
          const route = routes.get(role), busy = route && route.units > 0;
          if (role < 8 && busy) { x = point.x + (route.x - point.x) * travel + Math.cos(angle) * 6; y = point.y + (route.y - point.y) * travel + Math.sin(angle) * 6; }
          else if (role >= 8 && colony.buildings.length) {
            const building = colony.buildings[Math.floor(id / 10) % colony.buildings.length];
            if (building.status === 'working') { x = point.x + (building.x - point.x) * (.6 + .4 * travel) + Math.cos(angle) * 8; y = point.y + (building.y - point.y) * (.6 + .4 * travel) + Math.sin(angle) * 8; }
          }
          const paint = role < 8 ? this.catalog.items[role].color : color, r = z < .4 ? 2 / z : 3.1;
          this.circle(ctx, x, y, r, paint + 'cc', generation ? '#f0e9da77' : null, .7 / z);
          if (phase > .5 && busy && z > .5 && Math.floor(id / 10) < route.units) this.circle(ctx, x + 4, y - 3, 1.7, paint);
          if (z > .35) this.hits.push({type: 'inhabitant', x, y, radius: r, colonyId: colony.id, id, birth, role});
        }
      }
      if (own && ms < colony.move_at + colony.move_ms) {
        ctx.setLineDash([5 / z, 7 / z]); ctx.beginPath(); ctx.moveTo(point.x, point.y); ctx.lineTo(colony.to_x, colony.to_y); ctx.strokeStyle = '#bde3cd55'; ctx.lineWidth = 1 / z; ctx.stroke(); ctx.setLineDash([]);
        this.circle(ctx, colony.to_x, colony.to_y, 7 / z, null, '#c4dfcc88', 1 / z);
      }
      if (colony.neighbor && tick % 6 < 2 && z > .3) {
        const other = this.state.world.colonies.find(c => c.id === colony.neighbor);
        if (other && colony.id < other.id) { const q = position(other, ms); ctx.beginPath(); ctx.moveTo(point.x, point.y); ctx.lineTo(q.x, q.y); ctx.strokeStyle = '#daa7c42a'; ctx.lineWidth = 1 / z; ctx.setLineDash([2 / z, 10 / z]); ctx.stroke(); ctx.setLineDash([]); }
      }
      const level = 1 + Math.trunc(colony.experience / 250), r = clamp(13 + Math.log2(level + 1) * 2, 14, 32);
      this.circle(ctx, point.x, point.y, r + 8, color + '08', color + '25', .8 / z);
      const gradient = ctx.createRadialGradient(point.x - r * .3, point.y - r * .4, 1, point.x, point.y, r);
      gradient.addColorStop(0, '#e6f2d9'); gradient.addColorStop(.45, color); gradient.addColorStop(1, own ? '#546e7c' : '#43505b');
      this.circle(ctx, point.x, point.y, Math.max(r, 5 / z), gradient, color + 'aa', 1 / z);
      this.circle(ctx, point.x - r * .28, point.y - r * .35, r * .12, '#effce888');
      if (z > .12) { ctx.textAlign = 'center'; ctx.fillStyle = own ? '#d5ebdc' : '#b2c7c0'; ctx.font = `${11 / z}px system-ui`; ctx.fillText(colony.name, point.x, point.y - r - 17 / z);
        ctx.font = `${9 / z}px system-ui`; ctx.fillStyle = '#809c92'; ctx.fillText(`${own ? 'YOUR CORE · ' : ''}${count.toLocaleString()}人`, point.x, point.y + r + 19 / z); }
      this.hits.push({type: 'core', x: point.x, y: point.y, radius: r, colonyId: colony.id});
    }
    if (this.mode === 'build' && this.cursor && this.me) {
      const p = position(this.me, ms), reach = 190 + (this.me.research['1'] || 0) * 24;
      const good = Math.hypot(this.cursor.x - p.x, this.cursor.y - p.y) <= reach;
      this.circle(ctx, this.cursor.x, this.cursor.y, 18, good ? '#aad9b333' : '#de9e9633', good ? '#b3dec1' : '#dfaaa2', 1.5 / z);
    }
    document.getElementById('survey').classList.toggle('hidden', !aggregated);
  }
  loop(now) {
    if (!document.hidden && this.visible && now - this.lastDraw >= (this.reduced ? 200 : 25)) {
      this.lastDraw = now; this.draw(); this.frames++;
    }
    requestAnimationFrame(this.loop);
  }
}
