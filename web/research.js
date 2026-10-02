import {clamp, circle, makeOrb, researchOwned, researchReady} from './world.js';
const TAU=Math.PI*2;
// Each leaf receives a non-overlapping angular interval. Internal nodes sit at
// the weighted center of their descendants, so forks are structural, not jittered
// radial chains. The exact parent IDs are also enforced by the native server.
export function layoutResearch(catalog) {
  const nodes=catalog.research.map(node=>({...node,children:[],depth:1}));
  for(const node of nodes)if(node.parent>=0)nodes[node.parent].children.push(node.id);
  const leaves=id=>nodes[id].children.length?nodes[id].children.reduce((n,child)=>n+leaves(child),0):1;
  function place(id,lo,hi,depth,branchAngle){const node=nodes[id];node.depth=depth;
    const angle=branchAngle+(lo+hi)/2,radius=[0,145,285,425,605][depth]??(605+(depth-4)*160);
    node.angle=angle;node.x=Math.cos(angle)*radius;node.y=Math.sin(angle)*radius;
    let cursor=lo;const total=leaves(id);
    for(const child of node.children){const width=(hi-lo)*leaves(child)/total;place(child,cursor,cursor+width,depth+1,branchAngle);cursor+=width;}}
  for(const root of nodes.filter(n=>n.parent<0))place(root.id,-.32,.32,1,-Math.PI/2+root.branch*TAU/8);
  return nodes;
}
export class ResearchTree {
  constructor(canvas,onSelect){this.canvas=canvas;this.ctx=canvas.getContext('2d');this.onSelect=onSelect;
    this.opened=false;this.catalog=null;this.colony=null;this.camera={x:0,y:0,zoom:.6};this.nodes=[];this.selected=null;this.hover=null;
    this.orb=makeOrb();this.pointers=new Map();this.didFit=false;this.inset=0;this.bindInput();window.addEventListener('resize',()=>{this.resize();if(this.opened)this.fit();});}
  setCatalog(catalog){this.catalog=catalog;this.nodes=layoutResearch(catalog);}
  setColony(colony){this.colony=colony;if(this.opened)this.draw();}
  resize(){this.width=innerWidth;this.height=innerHeight;this.dpr=Math.min(2,devicePixelRatio||1);this.canvas.width=Math.round(this.width*this.dpr);this.canvas.height=Math.round(this.height*this.dpr);}
  origin(){return{x:this.width/2,y:(this.height+90)/2};}
  toWorld(x,y){const o=this.origin();return{x:this.camera.x+(x-o.x)/this.camera.zoom,y:this.camera.y+(y-o.y)/this.camera.zoom};}
  toScreen(x,y){const o=this.origin();return{x:o.x+(x-this.camera.x)*this.camera.zoom,y:o.y+(y-this.camera.y)*this.camera.zoom};}
  zoom(factor,x,y){const o=this.origin();x??=o.x;y??=o.y;const before=this.toWorld(x,y);this.camera.zoom=clamp(this.camera.zoom*factor,.15,2.5);
    const after=this.toWorld(x,y);this.camera.x+=before.x-after.x;this.camera.y+=before.y-after.y;this.draw();}
  open(){this.opened=true;this.resize();if(!this.didFit){this.fit();this.didFit=true;}else this.draw();}
  fit(){this.camera={x:0,y:0,zoom:clamp(Math.min(this.width-64,this.height-230)/1330,.15,.9)};this.draw();}
  focus(id){const node=this.nodes[id];if(!node)return;this.selected=id;
    this.camera.zoom=Math.max(this.camera.zoom,this.width<700?.66:.8);
    const target={x:this.width<700?this.width/2:(this.width-320)/2,y:this.height*(this.width<700?.35:.50)},o=this.origin();
    this.camera.x=node.x-(target.x-o.x)/this.camera.zoom;this.camera.y=node.y-(target.y-o.y)/this.camera.zoom;this.draw();}
  hit(x,y){const p=this.toWorld(x,y);let best=null,distance=Infinity;
    for(const node of this.nodes){const d=Math.hypot(node.x-p.x,node.y-p.y);if(d<Math.max(17,14/this.camera.zoom)&&d<distance){best=node;distance=d;}}return best;}
  bindInput(){const c=this.canvas;
    c.addEventListener('wheel',e=>{e.preventDefault();this.zoom(Math.exp(-clamp(e.deltaY,-200,200)*.0025),e.clientX,e.clientY);},{passive:false});
    c.addEventListener('pointerdown',e=>{if(e.button!==0)return;this.pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});c.setPointerCapture(e.pointerId);
      this.drag={x:e.clientX,y:e.clientY,cx:this.camera.x,cy:this.camera.y,moved:false};if(this.pointers.size===2){const[p,q]=[...this.pointers.values()];this.pinch=Math.hypot(p.x-q.x,p.y-q.y);this.gesture=true;}});
    c.addEventListener('pointermove',e=>{if(!this.pointers.has(e.pointerId)){const hit=this.hit(e.clientX,e.clientY);if(hit?.id!==this.hover){this.hover=hit?.id??null;this.draw();}c.style.cursor=hit?'pointer':'grab';return;}
      this.pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});
      if(this.pointers.size===2){const[p,q]=[...this.pointers.values()],d=Math.hypot(p.x-q.x,p.y-q.y);if(this.pinch>0)this.zoom(d/this.pinch,(p.x+q.x)/2,(p.y+q.y)/2);this.pinch=d;return;}
      if(!this.drag||this.gesture)return;const dx=e.clientX-this.drag.x,dy=e.clientY-this.drag.y;if(Math.hypot(dx,dy)>5)this.drag.moved=true;
      if(this.drag.moved){this.camera.x=this.drag.cx-dx/this.camera.zoom;this.camera.y=this.drag.cy-dy/this.camera.zoom;c.style.cursor='grabbing';this.draw();}});
    c.addEventListener('pointerup',e=>{const moved=this.gesture||this.drag?.moved;this.pointers.delete(e.pointerId);if(this.pointers.size){this.drag=null;return;}
      this.drag=null;this.gesture=false;this.pinch=0;if(!moved){const hit=this.hit(e.clientX,e.clientY);if(hit){this.selected=hit.id;this.onSelect(hit.id);this.draw();}}});
    c.addEventListener('pointercancel',()=>{this.drag=null;this.gesture=false;this.pointers.clear();});
    c.addEventListener('pointerleave',()=>{this.hover=null;if(this.opened)this.draw();});
  }
  drawLabels(research){
    const ctx=this.ctx,z=this.camera.zoom,selected=this.nodes[this.selected],labels=[];
    const near=node=>selected&&(node.parent===selected.id||node.id===selected.parent||node.parent===selected.parent);
    for(const node of this.nodes){const active=node.id===this.selected||node.id===this.hover,owned=researchOwned(research,node),ready=researchReady(research,node,this.catalog),family=node.parent<0;
      if(!family&&!active&&!ready&&!near(node)&&!(z>1.3||owned&&z>.95))continue;
      const p=this.toScreen(node.x,node.y);if(p.x<0||p.y<100||p.x>this.width||p.y>this.height-40)continue;
      labels.push({node,p,active,family,text:family?this.catalog.branches[node.branch].name:node.name,
        priority:active?0:family?1:ready?2:near(node)?3:owned?4:5,
        color:family?this.catalog.branches[node.branch].color:active?'#e4ecd9':owned?'#bcd0be':ready?'#aac8b9':'#91aaa0'});
    }
    ctx.setTransform(this.dpr,0,0,this.dpr,0,0);ctx.textAlign='center';ctx.textBaseline='middle';
    const placed=[];const overlaps=(a,b)=>a.x<b.x+b.w+4&&a.x+a.w+4>b.x&&a.y<b.y+b.h+3&&a.y+a.h+3>b.y;
    // Layout labels in screen space. Family names never shrink to illegible pixels,
    // and lower-priority text yields instead of overlapping a selected discovery.
    for(const label of labels.sort((a,b)=>a.priority-b.priority||a.node.id-b.node.id)){
      const {node,p,family,active}=label,font=active?11:this.width<700?9:10;ctx.font=`${font}px system-ui`;
      const w=ctx.measureText(label.text).width+4,h=font+4,r=Math.max(11,node.parent<0?13:10)*z;
      const radial={x:p.x+Math.cos(node.angle)*(r+22),y:p.y+Math.sin(node.angle)*(r+22)};
      const candidates=[...(family?[radial]:[]),{x:p.x,y:p.y+r+15},{x:p.x,y:p.y-r-15},
        {x:p.x+w/2+r+9,y:p.y},{x:p.x-w/2-r-9,y:p.y}];
      for(const q of candidates){const box={x:q.x-w/2,y:q.y-h/2,w,h};
        if(box.x<8||box.y<62||box.x+w>this.width-8||box.y+h>this.height-40)continue;
        if(box.x<310&&box.y<151)continue; // title area
        if(this.selected!==null&&this.width>700&&box.x+w>this.width-340&&box.y>85)continue;
        if(placed.some(old=>overlaps(box,old)))continue;
        const touches=this.nodes.some(other=>{if(other.id===node.id)return false;const v=this.toScreen(other.x,other.y);return v.x>box.x-6&&v.x<box.x+w+6&&v.y>box.y-6&&v.y<box.y+h+6;});
        if(touches)continue;
        ctx.strokeStyle='#102025dd';ctx.lineWidth=3;ctx.lineJoin='round';ctx.strokeText(label.text,q.x,q.y);ctx.fillStyle=label.color;ctx.fillText(label.text,q.x,q.y);
        placed.push({...box,id:node.id,text:label.text});break;
      }
    }
    this.labels=placed;ctx.textBaseline='alphabetic';
  }
  draw(){if(!this.opened||!this.catalog)return;const ctx=this.ctx,z=this.camera.zoom,o=this.origin(),research=this.colony?.research||{};
    ctx.setTransform(this.dpr,0,0,this.dpr,0,0);ctx.fillStyle='#101e22';ctx.fillRect(0,0,this.width,this.height);
    const bg=ctx.createRadialGradient(o.x,o.y,0,o.x,o.y,Math.max(this.width,this.height)*.64);bg.addColorStop(0,'#2d454747');bg.addColorStop(1,'#08171d00');ctx.fillStyle=bg;ctx.fillRect(0,0,this.width,this.height);
    ctx.setTransform(this.dpr*z,0,0,this.dpr*z,this.dpr*(o.x-this.camera.x*z),this.dpr*(o.y-this.camera.y*z));
    for(const node of this.nodes){const parent=node.parent<0?{x:0,y:0,angle:node.angle}:this.nodes[node.parent],owned=researchOwned(research,node),ready=researchReady(research,node,this.catalog),color=this.catalog.branches[node.branch].color;
      const distance=Math.hypot(node.x-parent.x,node.y-parent.y),control=distance*.5;
      ctx.beginPath();ctx.moveTo(parent.x,parent.y);ctx.bezierCurveTo(parent.x+Math.cos(parent.angle)*control,parent.y+Math.sin(parent.angle)*control,node.x-Math.cos(node.angle)*control,node.y-Math.sin(node.angle)*control,node.x,node.y);
      ctx.strokeStyle=color+(owned?'ad':ready?'6b':'22');ctx.lineWidth=(node.depth===1?2:node.depth===2?1.7:1.1)/z;ctx.stroke();}
    for(const node of this.nodes){const color=this.catalog.branches[node.branch].color,owned=researchOwned(research,node),ready=researchReady(research,node,this.catalog),active=this.selected===node.id||this.hover===node.id;
      if(ready||active){const glow=ctx.createRadialGradient(node.x,node.y,4,node.x,node.y,30);glow.addColorStop(0,color+'19');glow.addColorStop(1,color+'00');circle(ctx,node.x,node.y,30,glow);}
      const r=owned?11:ready?13:9;circle(ctx,node.x,node.y,r,owned?color+'a5':'#172a2d',color+(owned?'cc':ready?'c0':'4a'),(ready?1.5:1)/z);
      if(active)circle(ctx,node.x,node.y,r+7,null,color+'a0',1/z);
      if(owned){ctx.strokeStyle='#132628';ctx.lineWidth=1.7/z;ctx.beginPath();ctx.moveTo(node.x-4/z,node.y);ctx.lineTo(node.x-1/z,node.y+3/z);ctx.lineTo(node.x+5/z,node.y-4/z);ctx.stroke();}
      else if(ready)circle(ctx,node.x,node.y,2/z,color);

    }
    ctx.drawImage(this.orb,-38,-38,76,76);circle(ctx,0,0,49,null,'#afccae20',1/z);
    this.drawLabels(research);
  }
}
