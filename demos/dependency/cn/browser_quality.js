/* Actual SVG text bounds in the currently rendered browser; read-only geometry. */
window.diagramQuality = function (doc) {
  const svg=doc.querySelector('svg');
  if(!svg) return {status:'not-loaded', issues:[]};
  const issues=[], checked=[], sizes=[], allBounds=[];
  for(const group of doc.querySelectorAll('g[data-box]')) {
    const [x,y,w,h]=group.getAttribute('data-box').split(',').map(Number);
    const texts=[...group.querySelectorAll('text')];
    const previous=[];
    for(const text of texts) {
      const b=text.getBBox(), value=text.textContent;
      const matrix=text.getScreenCTM();
      if(value.trim() && matrix && (group.dataset.kind!=='text' || group.dataset.contentText==='true'))
        sizes.push(parseFloat(doc.defaultView.getComputedStyle(text).fontSize)*Math.hypot(matrix.a,matrix.b));
      for(const p of previous) {
        if(Math.min(b.x+b.width,p.x+p.width)-Math.max(b.x,p.x)>1 && Math.min(b.y+b.height,p.y+p.height)-Math.max(b.y,p.y)>1)
          issues.push({kind:'rendered-text-overlap',id:group.id||'edge-label',text:value});
      }
      previous.push(b);
      if(svg.dataset.quality==='refined' && value.trim()) {
        for(const p of allBounds) {
          if(p.group!==group && Math.min(b.x+b.width,p.box.x+p.box.width)-Math.max(b.x,p.box.x)>1 && Math.min(b.y+b.height,p.box.y+p.box.height)-Math.max(b.y,p.box.y)>1)
            issues.push({kind:'cross-group-text-overlap',text:value,other:p.text});
        }
        allBounds.push({group,box:b,text:value});
      }
      checked.push({id:group.id||'edge-label',text:value});
      if(b.x<x-2 || b.y<y-2 || b.x+b.width>x+w+2 || b.y+b.height>y+h+2)
        issues.push({kind:'rendered-text-overflow',id:group.id||'edge-label',text:value,box:[b.x,b.y,b.width,b.height],container:[x,y,w,h]});
      if(group.dataset.kind==='diamond') {
        const safe=(px,py)=>Math.abs((px-x-w/2)/(w/2))+Math.abs((py-y-h/2)/(h/2))<=1.02;
        if(![[b.x,b.y],[b.x+b.width,b.y],[b.x,b.y+b.height],[b.x+b.width,b.y+b.height]].every(([px,py])=>safe(px,py)))
          issues.push({kind:'text-outside-diamond',id:group.id,text:value});
      }
    }
  }
  const minimum=sizes.length?Math.min(...sizes):null;
  return {status:issues.length?'issues-found':'passed',texts:checked.length,issues,
    readability:{minimum_content_font_px:minimum===null?null:Math.round(minimum*100)/100,review_threshold_px:12,status:minimum===null?'not-measured':minimum<11.95?'review-required':'within-target'},
    scope:'actual SVG text bounds, text overlaps (also across groups for refined diagrams), diamond containment and displayed content font size; not aesthetic or native-editor approval'};
};
