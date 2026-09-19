/* Original, dependency-free MLP arithmetic for the network UI example. */
(function(root){
  function create(seed=42){
    let s=seed>>>0;
    const rand=()=>{s=(Math.imul(1664525,s)+1013904223)>>>0;return s/4294967296};
    const sizes=[8,14,10,3],weights=[],biases=[];
    for(let l=1;l<sizes.length;l++){
      const scale=Math.sqrt(6/sizes[l-1]);
      weights.push(Array.from({length:sizes[l]},()=>Array.from({length:sizes[l-1]},()=>(rand()*2-1)*scale)));
      biases.push(Array.from({length:sizes[l]},()=>(rand()*2-1)*.12));
    }
    return {sizes,weights,biases,seed,inputs:[.68,.35,.81,.42,.56,.23,.74,.49],synthetic:true,trained:false};
  }
  function validate(m){
    if(JSON.stringify(m.sizes)!=='[8,14,10,3]')throw Error('This example supports the 8 → 14 → 10 → 3 topology.');
    if(m.inputs.length!==8||!m.inputs.every(Number.isFinite))throw Error('Expected eight finite inputs.');
    if(m.weights.length!==3||m.biases.length!==3)throw Error('Expected three parameter layers.');
    for(let l=0;l<3;l++){
      if(m.weights[l].length!==m.sizes[l+1]||m.biases[l].length!==m.sizes[l+1])throw Error('Invalid layer size.');
      if(!m.weights[l].every(r=>r.length===m.sizes[l]&&r.every(Number.isFinite))||!m.biases[l].every(Number.isFinite))throw Error('Invalid parameters.');
    }
    return m;
  }
  function forward(m,inputs=m.inputs){
    validate(m);if(inputs.length!==8||!inputs.every(Number.isFinite))throw Error('Invalid inputs.');
    const a=[inputs.slice()],z=[];
    for(let l=0;l<3;l++){
      const v=m.weights[l].map((row,j)=>row.reduce((sum,w,i)=>sum+w*a[l][i],m.biases[l][j]));
      if(!v.every(Number.isFinite))throw Error('Non-finite forward arithmetic; reduce input/parameter magnitude.');
      z.push(v);
      if(l<2)a.push(v.map(x=>Math.max(0,x)));
      else{const mx=Math.max(...v),e=v.map(x=>Math.exp(x-mx)),sum=e.reduce((x,y)=>x+y,0);a.push(e.map(x=>x/sum));}
    }
    return {a,z};
  }
  const api={create,validate,forward};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.NetworkModel=api;
})(typeof globalThis!=='undefined'?globalThis:this);
