/* Offline reader controls. Diagram labels stay in the author's language. */
(() => {
  const {pages, language} = JSON.parse(document.querySelector('#reader-data').textContent);
  const pick=document.querySelector('#page'), obj=document.querySelector('object');
  const main=document.querySelector('main'), quality=document.querySelector('#quality');
  const words={
    zh:{page:'阅读页面',fit:'结构总览',read:'清晰阅读',width:'适合宽度',actual:'原始尺寸',source:'可编辑多页源',data:'内容数据',receipt:'交付记录',note:'总览看关系，详页读完整内容。',passed:'文字边界通过',issues:'文字边界需要复核',small:'字号偏小，可切换清晰阅读',font:'当前最小正文字号',unavailable:'浏览器未允许文字检查；可通过本地 HTTP 服务打开。'},
    en:{page:'Reading page',fit:'Overview',read:'Readable size',width:'Fit width',actual:'Actual size',source:'Editable pages',data:'Source data',receipt:'Delivery record',note:'Overview for relationships; detail pages for full content.',passed:'Text bounds passed',issues:'Review text bounds',small:'Small text; use Readable size',font:'Smallest displayed content text',unavailable:'Browser text check unavailable; open through a local HTTP server.'}
  };
  let lang=language, mode='auto', currentReport=null;
  function reportText(){
    const w=words[lang];
    if(!currentReport){quality.textContent=w.unavailable;return;}
    const r=currentReport.readability;
    quality.textContent=(currentReport.status==='passed'?w.passed:w.issues)+
      (r?.minimum_content_font_px!=null?` · ${w.font}: ${r.minimum_content_font_px}px`:'')+
      (r?.status==='review-required'?` · ${w.small}`:'');
  }
  async function check(){
    try{
      const doc=obj.contentDocument;
      if(!doc)throw new Error('SVG not accessible');
      await doc.fonts.ready;
      currentReport=diagramQuality(doc);
      quality.dataset.report=JSON.stringify(currentReport);
    }catch(_){currentReport=null;delete quality.dataset.report;}
    reportText();
  }
  function show(){
    const p=pages.find(x=>x.file===pick.value);
    const fit=Math.min((main.clientWidth-48)/p.width,(main.clientHeight-48)/p.height,1);
    const scale=mode==='actual'?1:mode==='width'?Math.min((main.clientWidth-48)/p.width,1):
      mode==='fit'?fit:Math.min(1,Math.max(fit,12/p.minimum_font));
    obj.style.width=p.width*Math.max(.01,scale)+'px';obj.style.height=p.height*Math.max(.01,scale)+'px';
    if(obj.getAttribute('data')!==p.file){
      currentReport=null;delete quality.dataset.report;quality.textContent='…';
      obj.data=p.file;main.scrollTop=0;main.scrollLeft=0;
    }
    else requestAnimationFrame(check);
    for(const button of document.querySelectorAll('[data-mode]'))
      button.setAttribute('aria-pressed',String(button.dataset.mode===mode || mode==='auto' && button.dataset.mode==='read'));
  }
  function translate(){
    document.documentElement.lang=lang==='zh'?'zh-CN':'en';
    for(const el of document.querySelectorAll('[data-i18n]'))el.textContent=words[lang][el.dataset.i18n];
    pick.setAttribute('aria-label',words[lang].page);reportText();show();
  }
  pick.addEventListener('change',()=>{mode='auto';show();});
  obj.addEventListener('load',check);
  for(const button of document.querySelectorAll('[data-mode]'))button.onclick=()=>{mode=button.dataset.mode;show();};
  const languagePick=document.querySelector('#language');languagePick.value=lang;
  languagePick.onchange=()=>{lang=languagePick.value;translate();};
  window.addEventListener('resize',show);translate();
})();
