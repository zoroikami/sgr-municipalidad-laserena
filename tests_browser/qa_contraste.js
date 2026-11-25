() => {
  const canvas=document.createElement('canvas');canvas.width=canvas.height=1;
  const ctx=canvas.getContext('2d',{willReadFrequently:true}),cache=new Map();
  function rgba(color){if(!cache.has(color)){ctx.clearRect(0,0,1,1);ctx.fillStyle=color;ctx.fillRect(0,0,1,1);cache.set(color,[...ctx.getImageData(0,0,1,1).data]);}return cache.get(color);}
  const over=(a,b)=>{const alpha=a[3]/255;return [0,1,2].map(i=>a[i]*alpha+b[i]*(1-alpha)).concat(255);};
  function background(el){const stack=[];for(let n=el;n;n=n.parentElement)stack.push(rgba(getComputedStyle(n).backgroundColor));let result=[255,255,255,255];for(const c of stack.reverse())result=over(c,result);return result;}
  const luminance=c=>c.slice(0,3).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;}).reduce((n,v,i)=>n+v*[.2126,.7152,.0722][i],0);
  const issues=[],seen=new Set(),walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let node;
  while(node=walker.nextNode()){
    if(!node.textContent.trim())continue;
    const el=node.parentElement,s=getComputedStyle(el),r=el.getBoundingClientRect();
    if(!r.width||!r.height||s.visibility==='hidden'||s.display==='none'||Number(s.opacity)<.8||el.closest('[disabled],.visually-hidden,script,style,option'))continue;
    const bg=background(el),fg=over(rgba(s.color),bg),a=luminance(fg),b=luminance(bg),ratio=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);
    const big=parseFloat(s.fontSize)>=24||(parseFloat(s.fontSize)>=18.66&&Number(s.fontWeight)>=700),minimum=big?3:4.5;
    const key=el.tagName+'.'+el.className+'|'+s.color+'|'+ratio.toFixed(2);
    if(ratio<minimum-.05&&!seen.has(key)){issues.push({elemento:el.id?'#'+el.id:el.tagName+'.'+el.className,texto:node.textContent.trim().slice(0,80),ratio:Number(ratio.toFixed(2)),minimo:minimum,color:s.color,fondo:bg.slice(0,3).map(Math.round)});seen.add(key);}
  }
  return issues;
}
