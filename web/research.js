import {clamp} from './world.js';
export class ResearchTree {
  constructor(canvas, onSelect) {
    this.canvas = canvas; this.ctx = canvas.getContext('2d'); this.onSelect = onSelect; this.opened = false;
    this.camera = {x: 0, y: 0, zoom: .8}; this.selected = null; this.catalog = null; this.colony = null;
    this.drag = null; this.nodes = [];
    canvas.addEventListener('wheel', e => { e.preventDefault(); this.zoom(Math.exp(-clamp(e.deltaY, -160, 160) * .002), e.clientX, e.clientY); }, {passive: false});
    canvas.addEventListener('pointerdown', e => { this.drag = {x: e.clientX, y: e.clientY, cx: this.camera.x, cy: this.camera.y, moved: false}; canvas.setPointerCapture(e.pointerId); });
    canvas.addEventListener('pointermove', e => { if (!this.drag) return; const dx = e.clientX - this.drag.x, dy = e.clientY - this.drag.y;
      if (Math.hypot(dx, dy) > 5) this.drag.moved = true;
      if (this.drag.moved) { this.camera.x = this.drag.cx - dx / this.camera.zoom; this.camera.y = this.drag.cy - dy / this.camera.zoom; this.draw(); } });
    canvas.addEventListener('pointerup', e => { const moved = this.drag?.moved; this.drag = null;
      if (!moved) { const p = this.toWorld(e.clientX, e.clientY); let best = null, distance = Infinity;
        for (const node of this.nodes) { const d = Math.hypot(node.x - p.x, node.y - p.y); if (d < Math.max(18, 14 / this.camera.zoom) && d < distance) { best = node; distance = d; } }
        if (best) { this.selected = best.id; this.onSelect(best.id); this.draw(); } } });
    canvas.addEventListener('pointercancel', () => { this.drag = null; });
    window.addEventListener('resize', () => this.resize());
  }
  setCatalog(catalog) { this.catalog = catalog; this.nodes = catalog.research.map(r => {
    const angle = -Math.PI / 2 + r.branch * Math.PI / 4 + Math.sin(r.tier * 1.618) * .09, radius = 80 + r.tier * 55;
    return {...r, x: Math.cos(angle) * radius, y: Math.sin(angle) * radius}; }); }
  setColony(colony) { this.colony = colony; if (this.opened) this.draw(); }
  resize() { this.width = innerWidth; this.height = innerHeight; this.dpr = Math.min(2, devicePixelRatio || 1);
    this.canvas.width = Math.round(this.width * this.dpr); this.canvas.height = Math.round(this.height * this.dpr); if (this.opened) this.draw(); }
  origin() { return {x: this.width < 700 ? this.width / 2 : (this.width - 300) / 2, y: this.height * (this.width < 700 ? .4 : .55)}; }
  toWorld(x, y) { const origin = this.origin(); return {x: this.camera.x + (x - origin.x) / this.camera.zoom, y: this.camera.y + (y - origin.y) / this.camera.zoom}; }
  zoom(factor, x, y) { const o = this.origin(); x ??= o.x; y ??= o.y; const before = this.toWorld(x, y); this.camera.zoom = clamp(this.camera.zoom * factor, .25, 2.5);
    const after = this.toWorld(x, y); this.camera.x += before.x - after.x; this.camera.y += before.y - after.y; this.draw(); }
  open() { this.opened = true; this.resize(); if (this.width < 700) this.camera.zoom = .65; this.draw(); }
  fit() { this.camera = {x: 0, y: 0, zoom: clamp(Math.min((this.width < 700 ? this.width - 30 : this.width - 350), this.height - 170) / 1580, .25, .9)}; this.draw(); }
  circle(ctx, x, y, r, fill, stroke, width) { ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = width; ctx.stroke(); } }
  draw() {
    if (!this.opened || !this.catalog) return; const ctx = this.ctx, z = this.camera.zoom, origin = this.origin();
    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0); ctx.fillStyle = '#11191f'; ctx.fillRect(0, 0, this.width, this.height);
    ctx.setTransform(this.dpr * z, 0, 0, this.dpr * z, this.dpr * (origin.x - this.camera.x * z), this.dpr * (origin.y - this.camera.y * z));
    for (const radius of [135, 355, 575, 740]) this.circle(ctx, 0, 0, radius, null, '#849c9510', .7 / z);
    for (const node of this.nodes) {
      const rank = this.colony?.research[String(node.branch)] || 0, color = this.catalog.branches[node.branch].color;
      const parent = node.tier === 1 ? {x: 0, y: 0} : this.nodes[node.id - 1];
      ctx.beginPath(); ctx.moveTo(parent.x, parent.y); ctx.lineTo(node.x, node.y); ctx.strokeStyle = node.tier <= rank ? color + '88' : color + '25'; ctx.lineWidth = (node.tier <= rank ? 2 : 1) / z; ctx.stroke();
    }
    for (const node of this.nodes) {
      const rank = this.colony?.research[String(node.branch)] || 0, color = this.catalog.branches[node.branch].color;
      const done = node.tier <= rank, next = node.tier === rank + 1;
      if (this.selected === node.id) this.circle(ctx, node.x, node.y, 24, color + '10', color + '99', 1 / z);
      this.circle(ctx, node.x, node.y, 15, done ? color + 'b0' : '#1c282e', done ? color : next ? color + 'cc' : color + '45', (next ? 2 : 1) / z);
      ctx.fillStyle = done ? '#15251e' : next ? '#dce8de' : '#78918a'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.font = `${Math.max(11, 10 / z)}px system-ui`; ctx.fillText(done ? '✓' : String(node.tier), node.x, node.y);
      if (node.tier === 1) { const norm = Math.hypot(node.x, node.y); ctx.fillStyle = color; ctx.font = `${12 / z}px system-ui`;
        ctx.fillText(this.catalog.branches[node.branch].name, node.x + node.x / norm * 34, node.y + node.y / norm * 34); }
    }
    this.circle(ctx, 0, 0, 39, '#b5d8bd1a', '#b9d9c0aa', 1.5 / z); this.circle(ctx, 0, 0, 30, '#b6d8c233', '#b6d8c255', .7 / z);
    ctx.textAlign = 'center'; ctx.fillStyle = '#cce6d3'; ctx.font = `${12 / z}px system-ui`; ctx.fillText('コア', 0, -7 / z);
    ctx.font = `${9 / z}px system-ui`; ctx.fillStyle = '#93b29e'; ctx.fillText(`Lv.${1 + Math.trunc((this.colony?.experience || 0) / 250)}`, 0, 12 / z);
    ctx.textBaseline = 'alphabetic';
  }
}
