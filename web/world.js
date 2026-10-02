// Presentation only. Resource arithmetic here describes the authoritative snapshot;
// it never changes inventories, time, population, ownership, or game rewards.
export const clamp = (value, low, high) => Math.max(low, Math.min(high, value));
export const mod = (value, divisor) => ((value % divisor) + divisor) % divisor;
export const smooth = (low, high, value) => { const x = clamp((value-low)/(high-low),0,1); return x*x*(3-2*x); };
export const LIFE_TICKS = 90;
export function population(colony, tick) {
  let count=0, capacity=0;
  for (const cohort of colony.cohorts) { count += clamp(tick-cohort.start+1,0,cohort.count); capacity += cohort.count; }
  return {count, capacity};
}
export function position(colony, ms) {
  const t=clamp(ms-colony.move_at,0,colony.move_ms)/Math.max(1,colony.move_ms);
  return {x:colony.from_x+Math.trunc((colony.to_x-colony.from_x)*t), y:colony.from_y+Math.trunc((colony.to_y-colony.from_y)*t)};
}
export function nodeAt(cx,cy) {
  const salt=mod(cx*92821+cy*68917+19139,2147483647);
  return {x:cx*128+24+mod(salt,80), y:cy*128+24+mod(Math.trunc(salt/97),80),
    kind:mod(cx+3*cy,8),tier:1+Math.trunc(Math.max(Math.abs(cx),Math.abs(cy))/8),key:`${cx}:${cy}`};
}
export function availableStock(node,tick) { return Math.min(180+node.tier*30,node.stock+Math.max(0,tick-node.tick)*(2+Math.trunc(node.tier/3))); }
const residentNames=['Ash','Wren','Lumi','Fern','Moss','Robin','Sage','Iris','Rowan','Aster','Willow','Briar','Clover','Reed','Fable','Juniper'];
export function inhabitantName(colony,id) { return residentNames[mod(id*7+colony.id*3,residentNames.length)]; }
const countResidue=(lo,hi,r)=>hi<lo?0:Math.floor((hi-r)/8)-Math.floor((lo-1-r)/8);
export function kindsInRect(x0,y0,x1,y1) {
  const counts=Array(8).fill(0);
  if(x1<x0||y1<y0)return counts;
  for(let y=0;y<8;y++) { const rows=countResidue(y0,y1,y); if(!rows)continue;
    for(let kind=0;kind<8;kind++)counts[kind]+=rows*countResidue(x0,x1,mod(kind-3*y,8)); }
  return counts;
}
// Exact aggregation, not a stride-selected representative deposit. Tier bands
// are clipped analytically and all eight resource residues are counted, including
// negative coordinates. Cost depends on region width, not visible deposit count.
export function regionBase(cx,cy,stride) {
  const x1=cx+stride-1,y1=cy+stride-1, counts=kindsInRect(cx,cy,x1,y1), capacity=Array(8).fill(0);
  const minAbs=(lo,hi)=>lo<=0&&hi>=0?0:Math.min(Math.abs(lo),Math.abs(hi));
  const low=1+Math.floor(Math.max(minAbs(cx,x1),minAbs(cy,y1))/8);
  const high=1+Math.floor(Math.max(Math.abs(cx),Math.abs(cy),Math.abs(x1),Math.abs(y1))/8);
  const clipped=r=>r<0?Array(8).fill(0):kindsInRect(Math.max(cx,-r),Math.max(cy,-r),Math.min(x1,r),Math.min(y1,r));
  let inner=clipped(8*(low-1)-1);
  for(let tier=low;tier<=high;tier++) { const outer=clipped(8*tier-1);
    for(let k=0;k<8;k++)capacity[k]+=(outer[k]-inner[k])*(180+tier*30); inner=outer; }
  return {cx,cy,stride,counts,capacity,tierLow:low,tierHigh:high};
}
export function researchOwned(research,node) {
  const legacy=research[`legacy:${node.branch}`] ?? research[String(node.branch)] ?? 0;
  return node.tier<=legacy || research[`node:${node.id}`]===1;
}
export function researchReady(research,node,catalog) {
  return !researchOwned(research,node)&&(node.parent<0||researchOwned(research,catalog.research[node.parent]));
}
export function lodForZoom(z) {
  const resource=smooth(.10,.22,z), detail=smooth(.6,1,z), people=smooth(.38,.7,z);
  const level=Math.max(0,Math.log2(56/(128*z))), exponent=Math.floor(level);
  return {resource,detail,people,region:1-resource,stride:2**exponent,blend:level-exponent,
    name:z<.15?'Atlas':z<.4?'Landscape':z<1.5?'Colony':'Close-up'};
}
const TAU=Math.PI*2;
export function circle(ctx,x,y,r,fill,stroke,width=1) {
  ctx.beginPath();ctx.arc(x,y,Math.max(.001,r),0,TAU);
  if(fill){ctx.fillStyle=fill;ctx.fill();}if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=width;ctx.stroke();}
}
// A reusable lit, translucent sphere. Surface normals, a specular lobe, rim light
// and interior filaments are baked once; no per-frame per-pixel work or downloads.
export function makeOrb(tint=[110,190,175]) {
  const size=256,canvas=document.createElement('canvas');canvas.width=canvas.height=size;
  const ctx=canvas.getContext('2d'),image=ctx.createImageData(size,size),p=image.data;
  for(let py=0;py<size;py++)for(let px=0;px<size;px++) {
    const x=(px+.5-size/2)/(size*.48),y=(py+.5-size/2)/(size*.48),r2=x*x+y*y;
    if(r2>1)continue;
    const z=Math.sqrt(1-r2),light=Math.max(0,-.43*x-.52*y+.738*z),fresnel=(1-z)**3;
    const spec=Math.max(0,-.23*x-.28*y+.932*z)**90;
    const filament=Math.max(0,Math.sin(10*x+4*Math.sin(3*y)+7*z)*Math.sin(11*y-3*x+4*z))**12;
    const heart=Math.exp(-((x+.02)**2+(y-.14)**2)*8)*(.22+.16*Math.sin(5*x+3*y+z));
    const shade=.10+.68*light+.11*filament+heart;
    const iridescence=.5+.5*Math.sin(7*z+3*x-2*y);
    const i=(py*size+px)*4;
    p[i]=clamp(tint[0]*shade+fresnel*(80+90*iridescence)+255*spec+filament*40,0,255);
    p[i+1]=clamp(tint[1]*shade+fresnel*130+255*spec+filament*50,0,255);
    p[i+2]=clamp(tint[2]*shade+fresnel*(200-60*iridescence)+245*spec+filament*60,0,255);
    p[i+3]=Math.round(255*clamp((1-Math.sqrt(r2))*size*.48,0,1));
  }
  ctx.putImageData(image,0,0);
  const glint=ctx.createRadialGradient(93,73,0,93,73,29);glint.addColorStop(0,'#f5fffda8');glint.addColorStop(.24,'#f5fffc47');glint.addColorStop(1,'#f5fffc00');
  circle(ctx,93,73,29,glint);return canvas;
}
function resourceSprite(kind,variant,color) {
  const canvas=document.createElement('canvas');canvas.width=canvas.height=160;const c=canvas.getContext('2d');c.translate(80,85);
  c.fillStyle='#030f1266';c.beginPath();c.ellipse(4,14,43,18,0,0,TAU);c.fill();
  const seed=variant*2.399;
  if(kind===0||kind===2) {
    // Real silhouettes with trunks that fork, rather than concentric resource discs.
    const scale=kind===0?1:.67;c.scale(scale,scale);
    c.strokeStyle='#719487';c.lineCap='round';c.lineWidth=4;c.beginPath();c.moveTo(0,19);c.lineTo(-2,-20);c.moveTo(-1,4);c.lineTo(-23,-16);c.moveTo(-2,-9);c.lineTo(19,-30);c.stroke();
    const leaves=[[-22,-22,21],[17,-30,23],[-2,-44,23],[0,-15,25]];
    for(let i=0;i<leaves.length;i++) { const [x,y,r]=leaves[i],g=c.createRadialGradient(x-7,y-8,2,x,y,r);
      g.addColorStop(0,kind===0?'#579978':'#a3ad6f');g.addColorStop(.6,kind===0?'#28574b':'#637749');g.addColorStop(1,'#193c35');circle(c,x+Math.sin(seed+i)*3,y,r,g,'#8fc29a22',.7); }
  } else if(kind===3) {
    c.strokeStyle='#b8a76e';c.lineWidth=1.5;
    for(let i=0;i<10;i++){const x=Math.sin(i*2.4+seed)*26,y=Math.cos(i*1.7)*9;c.beginPath();c.moveTo(x,15+y);c.quadraticCurveTo(x-4,-5+y,x+3,-25+y);c.stroke();
      c.fillStyle='#c7b781';c.beginPath();c.ellipse(x+2,-22+y,3,10,.35,0,TAU);c.fill();}
  } else if(kind===7) {
    for(let r=39;r>6;r-=7)circle(c,0,0,r,`rgba(73,144,158,${.08+(39-r)/250})`);
    c.strokeStyle='#8cbbbf65';c.lineWidth=1;c.beginPath();c.ellipse(-2,-3,31,23,-.2,Math.PI,TAU);c.stroke();
  } else if(kind===6) {
    for(let i=0;i<5;i++){const x=Math.sin(i*2.4+seed)*23,y=Math.cos(i*2.4)*12,h=24+(i%3)*8;
      c.fillStyle=['#817da8','#b7aed7','#646690'][i%3];c.beginPath();c.moveTo(x-7,y);c.lineTo(x-6,y-h);c.lineTo(x+1,y-h-9);c.lineTo(x+9,y-h+3);c.lineTo(x+7,y+2);c.closePath();c.fill();
      c.strokeStyle='#e1d4f03a';c.lineWidth=.7;c.stroke();}
  } else {
    const palette=kind===1?['#707f86','#a1a9aa','#526670']:kind===4?['#766b78','#a89596','#4a5661']:['#806b60','#b69b81','#625953'];
    for(let i=0;i<5;i++){const x=Math.sin(i*2.4+seed)*22,y=Math.cos(i*2.4)*15,r=13+(i%3)*4,g=c.createLinearGradient(x-r,y-r,x+r,y+r);
      g.addColorStop(0,palette[1]);g.addColorStop(.45,palette[0]);g.addColorStop(1,palette[2]);
      c.beginPath();for(let k=0;k<6;k++){const a=k*TAU/6+seed,rr=r*(.88+.12*Math.sin(i+k));c[k?'lineTo':'moveTo'](x+Math.cos(a)*rr,y+Math.sin(a)*rr*.8);}c.closePath();c.fillStyle=g;c.fill();c.strokeStyle='#d8e4da18';c.lineWidth=.8;c.stroke();}
  }
  return canvas;
}
export class WorldScene {
  constructor(canvas,onPick) {
    this.canvas=canvas;this.ctx=canvas.getContext('2d',{alpha:false});this.onPick=onPick;
    this.staticLayer=document.createElement('canvas');this.staticCtx=this.staticLayer.getContext('2d',{alpha:false});
    this.camera={x:-216,y:0,zoom:1.25};this.state=null;this.catalog=null;this.mode='inspect';this.buildKind=0;
    this.hits=[];this.staticHits=[];this.staticKey='';this.pointers=new Map();this.frames=0;this.lastDraw=0;this.lastSeen=performance.now();
    this.visible=true;this.selected=null;this.hover=null;this.cursor=null;this.dirty=true;this.regionCache=new Map();this.deficitCache=new Map();
    this.reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
    matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change',e=>{this.reduced=e.matches;this.dirty=true;});
    this.orbs=[makeOrb(),makeOrb([150,156,208]),makeOrb([204,170,117])];
    this.metrics={resourceSprites:0,resourceMarks:0,regionTiles:0,residents:0,coreMarkers:0,fullCores:0,frameMilliseconds:0};
    this.resize();window.addEventListener('resize',()=>this.resize());this.bindInput();
    this.loop=this.loop.bind(this);requestAnimationFrame(this.loop);
  }
  resize() {this.width=innerWidth;this.height=innerHeight;this.dpr=Math.min(2,devicePixelRatio||1);
    this.canvas.width=this.staticLayer.width=Math.round(this.width*this.dpr);this.canvas.height=this.staticLayer.height=Math.round(this.height*this.dpr);this.staticKey='';this.dirty=true;}
  setCatalog(catalog){this.catalog=catalog;this.sprites=catalog.raw.map((_,k)=>Array.from({length:3},(_,i)=>resourceSprite(k,i,catalog.items[k].color)));this.staticKey='';this.dirty=true;}
  setState(state){if(this.state?.world.tick!==state.world.tick)this.deficitCache.clear();this.state=state;this.lastSeen=performance.now();this.dirty=true;}
  get me(){return this.state?.world.colonies.find(c=>c.id===this.state.me);}
  time(){return this.state?(this.state.backlog_ticks>0?this.state.world.tick*10000:this.state.now_ms+Math.min(5000,performance.now()-this.lastSeen)):Date.now();}
  center(){if(this.me){const p=position(this.me,this.time());this.camera.x=p.x;this.camera.y=p.y;this.staticKey='';this.dirty=true;}}
  toWorld(x,y){return{x:this.camera.x+(x-this.width/2)/this.camera.zoom,y:this.camera.y+(y-this.height/2)/this.camera.zoom};}
  toScreen(x,y){return{x:(x-this.camera.x)*this.camera.zoom+this.width/2,y:(y-this.camera.y)*this.camera.zoom+this.height/2};}
  zoom(factor,sx=this.width/2,sy=this.height/2){const before=this.toWorld(sx,sy);this.camera.zoom=clamp(this.camera.zoom*factor,.02,4);
    const after=this.toWorld(sx,sy);this.camera.x=clamp(this.camera.x+before.x-after.x,-1e6,1e6);this.camera.y=clamp(this.camera.y+before.y-after.y,-1e6,1e6);
    this.staticKey='';this.dirty=true;this.onViewport?.();}
  bindInput(){
    const canvas=this.canvas;canvas.addEventListener('wheel',e=>{e.preventDefault();this.zoom(Math.exp(-clamp(e.deltaY,-200,200)*.0025),e.clientX,e.clientY);},{passive:false});
    canvas.addEventListener('pointerdown',e=>{if(e.button!==0)return;canvas.setPointerCapture(e.pointerId);this.pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});
      if(this.pointers.size===1)this.drag={x:e.clientX,y:e.clientY,cx:this.camera.x,cy:this.camera.y,moved:false};
      if(this.pointers.size===2){const[p,q]=[...this.pointers.values()];this.pinch={distance:Math.hypot(p.x-q.x,p.y-q.y),x:(p.x+q.x)/2,y:(p.y+q.y)/2};if(this.drag)this.drag.moved=true;this.gesture=true;}});
    canvas.addEventListener('pointermove',e=>{this.cursor=this.toWorld(e.clientX,e.clientY);this.dirty=true;
      if(!this.pointers.has(e.pointerId)){this.hover=this.pick(this.cursor);this.onHover?.(this.hover,e.clientX,e.clientY);return;}
      this.pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});
      if(this.pointers.size===2){const[p,q]=[...this.pointers.values()],d=Math.hypot(p.x-q.x,p.y-q.y),x=(p.x+q.x)/2,y=(p.y+q.y)/2;
        if(this.pinch?.distance>0){this.zoom(d/this.pinch.distance,x,y);this.camera.x-=(x-this.pinch.x)/this.camera.zoom;this.camera.y-=(y-this.pinch.y)/this.camera.zoom;}
        this.pinch={distance:d,x,y};this.staticKey='';return;}
      if(!this.drag||this.gesture)return;const dx=e.clientX-this.drag.x,dy=e.clientY-this.drag.y;if(Math.hypot(dx,dy)>5)this.drag.moved=true;
      if(this.drag.moved){this.camera.x=clamp(this.drag.cx-dx/this.camera.zoom,-1e6,1e6);this.camera.y=clamp(this.drag.cy-dy/this.camera.zoom,-1e6,1e6);this.staticKey='';canvas.style.cursor='grabbing';this.onHover?.(null);}});
    canvas.addEventListener('pointerup',e=>{const moved=this.drag?.moved||this.gesture;this.pointers.delete(e.pointerId);
      if(this.pointers.size){this.drag=null;return;}this.drag=null;this.pinch=null;this.gesture=false;canvas.style.cursor=this.mode==='build'?'crosshair':'grab';
      if(!moved&&e.button===0){const point=this.toWorld(e.clientX,e.clientY);this.onPick(this.mode==='build'?{type:'ground',...point}:this.pick(point));}});
    canvas.addEventListener('pointercancel',()=>{this.pointers.clear();this.drag=null;this.pinch=null;this.gesture=false;});
    canvas.addEventListener('pointerleave',()=>{this.hover=null;this.onHover?.(null);this.dirty=true;});
    canvas.addEventListener('contextmenu',e=>{e.preventDefault();this.onPick({type:'ground',...this.toWorld(e.clientX,e.clientY),move:true});});
    canvas.addEventListener('dblclick',e=>{if(this.camera.zoom<.3){const p=this.toWorld(e.clientX,e.clientY);this.camera.x=p.x;this.camera.y=p.y;this.zoom(2);}});
  }
  pick(point){const order={core:0,cluster:1,building:2,inhabitant:3,node:4,region:5};let best=null,score=Infinity;
    for(const hit of this.hits){const d=Math.hypot(point.x-hit.x,point.y-hit.y);
      if(hit.type==='region'){if(point.x<hit.left||point.x>hit.right||point.y<hit.top||point.y>hit.bottom)continue;}
      else if(d>Math.max(hit.radius,7/this.camera.zoom))continue;
      const s=order[hit.type]*1e8+d;if(s<score){score=s;best=hit;}}
    return best||{type:'ground',...point};}
  bounds(m=0){const z=this.camera.zoom;return{left:this.camera.x-this.width/(2*z)-m,right:this.camera.x+this.width/(2*z)+m,top:this.camera.y-this.height/(2*z)-m,bottom:this.camera.y+this.height/(2*z)+m};}
  transform(ctx){const z=this.camera.zoom;ctx.setTransform(this.dpr*z,0,0,this.dpr*z,this.dpr*(this.width/2-this.camera.x*z),this.dpr*(this.height/2-this.camera.y*z));}
  region(cx,cy,stride){const key=`${cx}:${cy}:${stride}`;let base=this.regionCache.get(key);
    if(!base){base=regionBase(cx,cy,stride);if(this.regionCache.size>4000)this.regionCache.clear();this.regionCache.set(key,base);}
    let deficits=this.deficitCache.get(stride);if(!deficits){deficits=new Map();const tick=this.state?.world.tick??0;
      for(const[key,node]of Object.entries(this.state?.world.nodes||{})){const[x,y]=key.split(':').map(Number),bucket=`${Math.floor(x/stride)*stride}:${Math.floor(y/stride)*stride}`;
        if(!deficits.has(bucket))deficits.set(bucket,Array(8).fill(0));deficits.get(bucket)[node.kind]+=180+node.tier*30-availableStock(node,tick);}
      this.deficitCache.set(stride,deficits);}
    const missing=deficits.get(`${cx}:${cy}`)||Array(8).fill(0),stock=base.capacity.map((n,k)=>n-missing[k]);
    return{...base,stock,total:stock.reduce((a,b)=>a+b,0),full:base.capacity.reduce((a,b)=>a+b,0)};
  }
  drawRegions(ctx,bounds,stride,opacity,hits){if(opacity<.001)return;const size=128*stride,z=this.camera.zoom;ctx.globalAlpha=opacity;
    for(let cy=Math.floor(bounds.top/size)*stride;cy*128<bounds.bottom;cy+=stride)for(let cx=Math.floor(bounds.left/size)*stride;cx*128<bounds.right;cx+=stride){
      const r=this.region(cx,cy,stride),x=cx*128,y=cy*128,depletion=1-r.total/r.full;
      // A quiet land field, not enlarged deposit dots. Depleted regions retain a
      // stock-derived amber tint. Hover/click reveals exact per-resource totals.
      const richness=Math.min(1,Math.log2(r.tierLow+1)/8);ctx.fillStyle=`rgba(${23+Math.round(depletion*30+richness*6)},${42+Math.round(richness*9)},${43-Math.round(depletion*8)},.42)`;
      ctx.fillRect(x+.4/z,y+.4/z,size-.8/z,size-.8/z);
      if(depletion>.008){ctx.fillStyle=`rgba(206,163,103,${Math.min(.55,depletion)})`;ctx.fillRect(x+3/z,y+size-4/z,(size-6/z)*depletion,1.3/z);}
      // A tiny composition glyph represents the whole region, not one sampled
      // deposit. All eight kinds retain their own mark; depleted stock fades but
      // never disappears from inspection. Glyphs stay small in screen pixels.
      const middleX=x+size/2,middleY=y+size/2,extent=Math.min(5.2,size*z*.14);
      for(let k=0;k<8;k++){if(!r.counts[k])continue;const angle=-Math.PI/2+k*TAU/8,full=r.capacity[k],fraction=full?r.stock[k]/full:0;
        ctx.globalAlpha=opacity*(.10+.45*Math.sqrt(Math.max(0,fraction)));
        circle(ctx,middleX+Math.cos(angle)*extent/z,middleY+Math.sin(angle)*extent/z,1/z,this.catalog.items[k].color);
        this.metrics.regionalResourceMarks++;}
      ctx.globalAlpha=opacity;
      this.metrics.regionTiles++;
      if(hits)this.staticHits.push({type:'region',x:x+size/2,y:y+size/2,left:x,right:x+size,top:y,bottom:y+size,radius:size/2,summary:r});
    }ctx.globalAlpha=1;
  }
  staticWorld(){const z=this.camera.zoom,tick=this.state?.world.tick??0,key=`${this.width}:${this.height}:${this.camera.x}:${this.camera.y}:${z}:${tick}`;
    if(key===this.staticKey)return;this.staticKey=key;const ctx=this.staticCtx;this.staticHits=[];
    this.metrics.resourceSprites=0;this.metrics.resourceMarks=0;this.metrics.regionTiles=0;this.metrics.regionalResourceMarks=0;
    ctx.setTransform(this.dpr,0,0,this.dpr,0,0);ctx.fillStyle='#111e22';ctx.fillRect(0,0,this.width,this.height);
    const glow=ctx.createRadialGradient(this.width*.48,this.height*.47,10,this.width*.5,this.height*.5,Math.max(this.width,this.height)*.7);
    glow.addColorStop(0,'#233b3d6a');glow.addColorStop(1,'#08171d40');ctx.fillStyle=glow;ctx.fillRect(0,0,this.width,this.height);
    this.transform(ctx);const b=this.bounds(72),lod=lodForZoom(z);if(!this.catalog)return;
    this.drawRegions(ctx,b,Math.max(1,lod.stride),lod.region*(1-lod.blend),lod.blend<.5);
    this.drawRegions(ctx,b,Math.max(2,lod.stride*2),lod.region*lod.blend,lod.blend>=.5);
    if(lod.resource>.001){ctx.globalAlpha=lod.resource;
      for(let cy=Math.floor(b.top/128);cy<=Math.floor(b.bottom/128);cy++)for(let cx=Math.floor(b.left/128);cx<=Math.floor(b.right/128);cx++){
        const node=nodeAt(cx,cy),stored=this.state?.world.nodes[node.key],capacity=180+30*node.tier,stock=stored?availableStock(stored,tick):capacity;
        const fraction=stock/capacity,color=this.catalog.items[node.kind].color,variant=mod(cx*3+cy,3),size=68;
        if(lod.detail>.001){ctx.globalAlpha=lod.resource*lod.detail*(.24+.76*Math.sqrt(fraction));ctx.drawImage(this.sprites[node.kind][variant],node.x-size/2,node.y-size/2,size,size);this.metrics.resourceSprites++;}
        if(lod.detail<.999){ctx.globalAlpha=lod.resource*(1-lod.detail);circle(ctx,node.x,node.y,Math.max(5.5,1.1/z),color+(fraction>.02?'aa':'28'));circle(ctx,node.x,node.y,11,null,color+'17',.8/z);this.metrics.resourceMarks++;}
        if(lod.resource>.5)this.staticHits.push({type:'node',...node,stock,capacity,radius:lod.detail>.4?25:11});
      }ctx.globalAlpha=1;}
    if(z<.18){const step=2**Math.max(0,Math.ceil(Math.log2(90/(1024*z)))),max=Math.ceil(Math.max(Math.abs(b.left),Math.abs(b.right),Math.abs(b.top),Math.abs(b.bottom))/1024);
      ctx.strokeStyle='#94b4a326';ctx.lineWidth=.65/z;
      for(let tier=step;tier<=max;tier+=step){const left=(-8*tier+1)*128,right=8*tier*128;
        if(left>b.right||right<b.left||left>b.bottom||right<b.top)continue;
        ctx.strokeRect(left,left,right-left,right-left);const p=this.toScreen(right,left);
        if(p.x>65&&p.x<this.width-30&&p.y>100&&p.y<this.height-65){ctx.font=`${9/z}px system-ui`;ctx.fillStyle='#94b4a381';ctx.textAlign='right';ctx.fillText(`Tier ${tier}`,right-7/z,left+14/z);}}
    }
    // Fine, world-anchored dust. It fades out rather than expanding when zooming.
    if(z>.65){ctx.fillStyle='#b0c4b10d';for(let cy=Math.floor(b.top/64);cy<b.bottom/64;cy++)for(let cx=Math.floor(b.left/64);cx<b.right/64;cx++){
      const n=mod(cx*3911+cy*6389,103);circle(ctx,cx*64+n%51,cy*64+mod(n*13,53),.6,'#c5d7c818');}}
  }
  drawWorkshop(ctx,building,colony,color,z,lod){const p=this.toScreen(building.x,building.y);if(p.x< -40||p.y< -40||p.x>this.width+40||p.y>this.height+40)return;
    if(z<.2)return;const active=building.status==='working',r=15;ctx.globalAlpha=smooth(.18,.4,z);
    ctx.save();ctx.translate(building.x,building.y);cylinder(ctx,color,active);ctx.restore();
    if(z>.6&&this.selected?.type==='building'&&this.selected.id===building.id&&this.selected.colonyId===colony.id){const recipe=this.catalog.recipes[building.recipe];
      ctx.beginPath();ctx.arc(building.x,building.y,r+8,-Math.PI/2,-Math.PI/2+TAU*building.progress/recipe.period);ctx.strokeStyle=color;ctx.lineWidth=1.5/z;ctx.stroke();}
    ctx.globalAlpha=1;this.hits.push({type:'building',x:building.x,y:building.y,radius:19,colonyId:colony.id,id:building.id});
  }
  drawResidents(ctx,colony,point,ms,lod,z){if(lod.people<.001)return;const tick=this.state.world.tick,count=population(colony,tick).count;
    const stride=Math.max(1,Math.ceil(count/(z<.8?150:650))),routes=new Map(colony.routes.map(r=>[r.job,r]));let rendered=0;
    for(const group of colony.cohorts){const active=clamp(tick-group.start+1,0,group.count);
      for(let i=mod(-group.first,stride);i<active;i+=stride){const id=group.first+i,role=id%10,birth=group.start+i;
        const angle=id*2.39996+colony.id,phase=this.reduced ? .4 : mod(ms/14000+id*.137,1),t=.5-.5*Math.cos(phase*TAU),orbit=28+(id%17)*2;
        let x=point.x+Math.cos(angle)*orbit,y=point.y+Math.sin(angle)*orbit;const route=routes.get(role),busy=route&&route.units>0;
        if(role<8&&busy){x=point.x+(route.x-point.x)*t+Math.cos(angle)*7;y=point.y+(route.y-point.y)*t+Math.sin(angle)*7;}
        else if(role>=8&&colony.buildings.length){const target=colony.buildings[Math.floor(id/10)%colony.buildings.length];if(target.status==='working'){x=target.x+Math.cos(angle)*11;y=target.y+Math.sin(angle)*9;}}
        const s=this.toScreen(x,y);if(s.x< -8||s.y< -8||s.x>this.width+8||s.y>this.height+8)continue;
        const color=role<8?this.catalog.items[role].color:'#b8d4c6';ctx.globalAlpha=lod.people*.8;circle(ctx,x+1,y+2,2.3,'#0005');circle(ctx,x,y,2.6,color);
        if(z>1.6){circle(ctx,x-.5,y-.7,.7,'#edf6e4b0');if(busy&&phase>.5)circle(ctx,x+3,y-2,1,color);}
        if(z>.65)this.hits.push({type:'inhabitant',x,y,radius:3,colonyId:colony.id,id,birth,role});rendered++;}
    }ctx.globalAlpha=1;this.metrics.residents+=rendered;
  }
  drawCore(ctx,colony,point,z,ms){const own=colony.id===this.state.me,level=1+Math.trunc(colony.experience/250),r=clamp(19+Math.log2(level+1)*1.7,20,35);
    const color=own?'#a9dacd':this.catalog.branches[mod(colony.id+2,8)].color;
    const selected=this.selected?.type==='core'&&this.selected.colonyId===colony.id,hover=this.hover?.type==='core'&&this.hover.colonyId===colony.id;
    const detailed=smooth(.15,.3,z);
    if(detailed>0){ctx.globalAlpha=detailed;
      const g=ctx.createRadialGradient(point.x,point.y,r*.25,point.x,point.y,r*2.8);g.addColorStop(0,color+'16');g.addColorStop(1,color+'00');circle(ctx,point.x,point.y,r*2.8,g);
      ctx.fillStyle='#020e1580';ctx.beginPath();ctx.ellipse(point.x+3,point.y+r*.64,r*.9,r*.4,0,0,TAU);ctx.fill();
      const lift=this.reduced?0:Math.sin(ms/2700+colony.id)*1.2;ctx.drawImage(this.orbs[own?0:1+colony.id%2],point.x-r,point.y-r-3+lift,r*2,r*2);
      this.metrics.fullCores++;ctx.globalAlpha=1;}
    if(detailed<1){ctx.globalAlpha=1-detailed;circle(ctx,point.x,point.y,own?4/z:3/z,color);if(own)circle(ctx,point.x,point.y,9/z,null,color+'80',1/z);this.metrics.coreMarkers++;ctx.globalAlpha=1;}
    if(selected||hover){circle(ctx,point.x,point.y,r+8/z,null,color+'77',1/z);if(z>.25){const radius=190+(colony.research['1']||0)*24;circle(ctx,point.x,point.y,radius,null,color+'25',1/z);}}
    if(selected||hover||(own&&z<.35)){ctx.textAlign='center';ctx.fillStyle='#d2e3d9';ctx.font=`${11/z}px system-ui`;ctx.fillText(colony.name,point.x,point.y-Math.max(r,6/z)-14/z);}
    this.hits.push({type:'core',x:point.x,y:point.y,radius:Math.max(r,6/z),colonyId:colony.id});
  }
  draw(){const started=performance.now();this.staticWorld();const ctx=this.ctx,z=this.camera.zoom,lod=lodForZoom(z);
    ctx.setTransform(1,0,0,1,0,0);ctx.drawImage(this.staticLayer,0,0);this.transform(ctx);this.hits=this.staticHits.slice();
    this.metrics.residents=this.metrics.coreMarkers=this.metrics.fullCores=0;if(!this.state||!this.catalog)return;
    const ms=this.time(),tick=this.state.world.tick,farClusters=new Map();
    for(const colony of this.state.world.colonies){if(colony.created_tick>tick)continue;const point=position(colony,ms),p=this.toScreen(point.x,point.y),own=colony.id===this.state.me;
      for(const building of colony.buildings)this.drawWorkshop(ctx,building,colony,this.catalog.branches[mod(colony.id,8)].color,z,lod);
      if(p.x< -600*z||p.y< -600*z||p.x>this.width+600*z||p.y>this.height+600*z)continue;
      this.drawResidents(ctx,colony,point,ms,lod,z);
      if(z<.22&&!own){const key=`${Math.floor(p.x/26)}:${Math.floor(p.y/26)}`;if(!farClusters.has(key))farClusters.set(key,[]);farClusters.get(key).push({colony,point});continue;}
      if(own&&ms<colony.move_at+colony.move_ms){ctx.setLineDash([2/z,7/z]);ctx.beginPath();ctx.moveTo(point.x,point.y);ctx.lineTo(colony.to_x,colony.to_y);ctx.strokeStyle='#abd6c94a';ctx.lineWidth=1/z;ctx.stroke();ctx.setLineDash([]);
        circle(ctx,colony.to_x,colony.to_y,5/z,null,'#d3e6d77a',1/z);}
      this.drawCore(ctx,colony,point,z,ms);
    }
    for(const group of farClusters.values()){if(group.length===1){this.drawCore(ctx,group[0].colony,group[0].point,z,ms);continue;}
      const x=group.reduce((n,c)=>n+c.point.x,0)/group.length,y=group.reduce((n,c)=>n+c.point.y,0)/group.length;
      circle(ctx,x,y,10/z,'#1d333ee6','#9db4c171',1/z);ctx.textAlign='center';ctx.textBaseline='middle';ctx.font=`${10/z}px system-ui`;ctx.fillStyle='#d0dbde';ctx.fillText(String(group.length),x,y);ctx.textBaseline='alphabetic';
      this.hits.push({type:'cluster',x,y,radius:12/z,colonies:group.map(c=>c.colony.id)});this.metrics.coreMarkers++;}
    const highlighted=this.hover?.type==='node'?this.hover:this.selected?.type==='node'?this.selected:null;
    if(highlighted&&lod.resource>.5)circle(ctx,highlighted.x,highlighted.y,28,null,'#c7dec958',1/z);
    if(this.mode==='build'&&this.cursor&&this.me){const p=position(this.me,ms),range=190+(this.me.research['1']||0)*24;
      const good=Math.hypot(this.cursor.x-p.x,this.cursor.y-p.y)<=range&&this.me.buildings.every(b=>Math.hypot(b.x-this.cursor.x,b.y-this.cursor.y)>=24);
      circle(ctx,p.x,p.y,range,null,'#abd6c933',1/z);circle(ctx,this.cursor.x,this.cursor.y,19,good?'#9fd4bd20':'#da9c9720',good?'#b9e0cb':'#ddaba3',1.2/z);}
    this.metrics.frameMilliseconds=performance.now()-started;this.metrics.lod=lod.name;this.metrics.aggregateStride=lod.stride;this.metrics.populationSampling=lod.people>0;
  }
  loop(now){if(!document.hidden&&this.visible){const animating=!this.reduced&&!!this.state&&this.camera.zoom>.18;
      if((this.dirty||animating)&&now-this.lastDraw>(animating?33:100)){this.lastDraw=now;this.draw();this.frames++;this.dirty=false;}}
    requestAnimationFrame(this.loop);}
}
function cylinder(ctx,color,active){
  ctx.fillStyle='#050e1650';ctx.beginPath();ctx.ellipse(3,12,19,8,0,0,TAU);ctx.fill();
  ctx.fillStyle=active?'#436962':'#33494a';ctx.beginPath();ctx.roundRect(-13,-5,26,19,4);ctx.fill();
  ctx.fillStyle=active?'#7a9d89':'#5c736b';ctx.beginPath();ctx.moveTo(-17,-5);ctx.lineTo(-1,-17);ctx.lineTo(17,-5);ctx.lineTo(0,3);ctx.closePath();ctx.fill();
  ctx.strokeStyle='#d0dcc342';ctx.lineWidth=.7;ctx.stroke();ctx.fillStyle=active?'#ead3a0':'#405753';ctx.fillRect(-6,3,4,6);ctx.fillRect(4,1,4,6);
}
