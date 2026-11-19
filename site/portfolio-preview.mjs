// Row calculations must not depend on unrelated, incomplete form rows.
const number=v=>v===''||v===null||v===undefined?NaN:Number(v);
export function holdingPreview(r,futures=false){
 const qty=number(r.qty),cost=number(futures?r.entry:r.avg),price=number(futures?r.mark:r.price);
 if(![qty,cost,price].every(Number.isFinite)||qty<0||cost<=0||price<=0)return null;
 const sign=futures&&r.direction==='SHORT'?-1:1;
 const pnl=sign*qty*(price-cost),pct=sign*(price-cost)/cost*100,loss=number(r.lossPct);
 const cut=Number.isFinite(loss)&&loss>0&&loss<100?cost*(1-sign*loss/100):null;
 return {value:qty*price,pnl,pct,cut};
}
export function portfolioPreview(m){
 let nav=0,pnl=0,incomplete=0;
 for(const r of m.assets){const q=number(r.qty),p=number(r.price);if(!r.asset||!Number.isFinite(q)||!Number.isFinite(p)||q<0||p<=0){incomplete++;continue;}nav+=q*p;const v=holdingPreview(r);if(v)pnl+=v.pnl;}
 if(m.hasFutures){const wallet=number(m.wallet),positions=m.positions.map(r=>holdingPreview(r,true));if(!Number.isFinite(wallet)||wallet<0||positions.some(x=>!x))incomplete++;else{const u=positions.reduce((a,x)=>a+x.pnl,0);nav+=wallet+u;pnl+=u;}}
 return {nav,pnl,incomplete};
}

// Isolated asset threshold: stablecoins and all other holdings retain current value.
// This is a conditional portfolio boundary, never an asset-cost stop or forecast.
export function portfolioLossThreshold(m,index,pct){
 const v=portfolioPreview(m),r=m.assets[index],risk=number(pct);
 if(v.incomplete||m.hasFutures||!r||r.kind!=='spot'||!Number.isFinite(risk)||risk<=0||risk>=100||v.nav<=0)return null;
 const qty=number(r.qty),price=number(r.price);if(!Number.isFinite(qty)||qty<=0||!Number.isFinite(price)||price<=0)return null;
 const floor=v.nav*(1-risk/100),otherValue=v.nav-qty*price,raw=(floor-otherValue)/qty;
 return {nav:v.nav,floor,otherValue,price:raw>=0?raw:null,reachable:raw>=0,otherAssetsFixed:true};
}
