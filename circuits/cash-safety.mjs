// Draft numeric circuit. Exact unsigned integer arithmetic, not deployed.
// Inputs: cashAfterCents[24], navAfterCents[24], minimumCashBps[14], LSB first.
export function cashSafetyDraft(){
 const gates=[],width=38,cache=new Map();let next=64;
 const rawNand=(a,b)=>{gates.push([a,b]);return next++;};
 const nand=(a,b)=>{if(a===0||b===0)return 1;if(a===1&&b===1)return 0;const key=[Math.min(a,b),Math.max(a,b)].join(',');if(cache.has(key))return cache.get(key);const out=rawNand(a,b);cache.set(key,out);return out;},not=a=>nand(a,a),and=(a,b)=>not(nand(a,b)),or=(a,b)=>nand(not(a),not(b));
 const xor=(a,b)=>{const n=nand(a,b);return nand(nand(a,n),nand(b,n));};
 const add=(a,b)=>{let carry=0;return Array.from({length:width},(_,i)=>{const x=a[i]||0,y=b[i]||0,n=nand(x,y),t=nand(nand(x,n),nand(y,n)),u=nand(t,carry),sum=nand(nand(t,u),nand(carry,u));carry=nand(n,u);return sum;});};
 const ge=(a,b)=>{let equal=1,greater=0;for(let i=width-1;i>=0;i--){const x=a[i]||0,y=b[i]||0;greater=or(greater,and(equal,and(x,not(y))));equal=and(equal,not(xor(x,y)));}return or(greater,equal);};
 const cash=Array.from({length:24},(_,i)=>2+i),nav=Array.from({length:24},(_,i)=>26+i),bps=Array.from({length:14},(_,i)=>50+i);
 const constant=n=>Array.from({length:width},(_,i)=>Number((BigInt(n)>>BigInt(i))&1n));
 let lhs=Array(width).fill(0),rhs=Array(width).fill(0);
 // Multiplication by 10000 and by variable basis points; 38 bits hold every product.
 for(let i=0;i<14;i++){if((10000>>i)&1)lhs=add(lhs,[...Array(i).fill(0),...cash]);const part=[...Array(i).fill(0),...nav.map(n=>and(n,bps[i]))];rhs=add(rhs,part);}
 let nonzero=0;for(const n of nav)nonzero=or(nonzero,n);
 const valid=and(nonzero,and(ge(nav,cash),ge(constant(10000),bps))),pass=and(valid,ge(lhs,rhs));
 // Contract outputs are last two produced signals; append copies in that order.
 const nv=not(valid),np=not(pass),validOut=rawNand(nv,nv),passOut=rawNand(np,np);
 const u24=n=>n.toString(16).padStart(6,'0');
 return {schema:'decision-check.cash-safety-draft.v1',status:'NOT_DEPLOYED',rule:'valid AND cashAfterCents * 10000 >= navAfterCents * minimumCashBps',nIn:62,nOut:2,nState:0,gateCount:gates.length,netlist:'0x'+gates.map(([a,b])=>'00'+u24(a)+u24(b)).join(''),outputs:['valid','pass'],outputSignals:[validOut,passOut],ranges:{cashAfterCents:[0,16777215],navAfterCents:[1,16777215],minimumCashBps:[0,10000]},precision:'USD cents; basis points (0.01%). Reject out-of-range input. Never round monetary inputs silently.',assumptions:'Spot pilot; only cash/NAV inequality, not market analysis or input authenticity. Must benchmark X Layer gas and fees before deployment.'};
}
export function packCashInputs(cash,nav,bps){if(![cash,nav,bps].every(Number.isSafeInteger)||cash<0||nav<=0||cash>nav||nav>16777215||bps<0||bps>10000)throw Error('CASH_CIRCUIT_INPUT_OUT_OF_RANGE');return [...Array.from({length:24},(_,i)=>(cash>>i)&1),...Array.from({length:24},(_,i)=>(nav>>i)&1),...Array.from({length:14},(_,i)=>(bps>>i)&1)];}
export function evalNandDraft(d,inputs){if(inputs.length!==d.nIn||inputs.some(x=>x!==0&&x!==1))throw Error('INVALID_BITS');const signals=[0,1,...inputs],raw=d.netlist.slice(2);if(raw.length%14)throw Error('TRUNCATED_NETLIST');for(let i=0;i<raw.length;i+=14){if(raw.slice(i,i+2)!=='00')throw Error('UNSUPPORTED_OPCODE');const a=parseInt(raw.slice(i+2,i+8),16),b=parseInt(raw.slice(i+8,i+14),16);if(a>=signals.length||b>=signals.length)throw Error('FUTURE_SIGNAL');signals.push(Number(!(signals[a]&&signals[b])));}return signals.slice(-d.nOut);}
