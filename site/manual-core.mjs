// Browser-local scenario arithmetic, not account reconciliation or a trade engine.
export const profiles=Object.freeze({cycle:['1M','1w','1d'],swing:['1d','4h','1h'],intraday:['4h','1h','15m']});
const intents={spot:['BUY_SPOT','REVIEW_SPOT'],futures:['REVIEW_FUTURES']};
function number(x,key,min=0,max=1e12){const v=x[key];if(typeof v!=='number'||!Number.isFinite(v)||v<min||v>max)throw Error('INVALID_'+key);return v;}
const cents=n=>Math.round((n+Number.EPSILON)*100);
export function evaluateManual(x){
 if(!Object.hasOwn(profiles,x.profile)||!Object.hasOwn(intents,x.product)||!intents[x.product].includes(x.intent))throw Error('INVALID_SCOPE');
 if(typeof x.asset!=='string'||!/^[A-Z0-9][A-Z0-9._-]{0,19}$/.test(x.asset))throw Error('INVALID_ASSET');
 if(typeof x.venue!=='string'||!x.venue.trim()||x.venue.length>80)throw Error('INVALID_VENUE');
 const price=number(x,'price',1e-8,1e9),qty=number(x,'qty',0,1e9),budget=number(x,'budget');
 const context={asset:x.asset,venue:x.venue,product:x.product,intent:x.intent,profile:x.profile,requestedTimeframes:profiles[x.profile],source:'SELF_REPORTED',marketEvidence:'NOT_RUN',tapeout:'NOT_REQUESTED'};
 if(x.product==='spot'){
  const cost=number(x,'cost'),cash=number(x,'cash'),other=number(x,'other'),buy=number(x,'buy'),reserve=number(x,'reserve'),limit=number(x,'limit',0,100),scenarioPrice=number(x,'scenarioPrice',1e-8,1e9);
  if(qty===0&&cost!==0)throw Error('COST_WITHOUT_HOLDINGS');
  const value=qty*price,nav=value+cash+other;
  if(nav<=0||nav>1e15)throw Error('INVALID_NAV');
  if(x.intent==='REVIEW_SPOT'&&buy!==0)throw Error('REVIEW_HAS_PURCHASE');
  const postQty=qty+buy/price,postCash=cents(cash)-cents(buy),postValue=value+buy,weight=postValue/nav*100;
  const oldPnl=value-cost,newPnl=postValue-(cost+buy),scenarioPnl=postQty*scenarioPrice-(cost+buy),lossFromNow=Math.max(0,postQty*(price-scenarioPrice));
  const checks=[{key:'cash',pass:cents(buy)<=cents(cash)},{key:'reserve',pass:postCash>=cents(reserve)},{key:'allocation',pass:weight<=limit+1e-9},{key:'lossBudget',pass:lossFromNow<=budget+1e-9}];
  return {context,metrics:{nav,currentValue:value,currentPnl:oldPnl,currentAverage:qty?cost/qty:null,postQty,postCash:postCash/100,postWeight:weight,postAverage:postQty?(cost+buy)/postQty:null,postPnl:newPnl,scenarioPnl,lossFromNow},checks,status:checks.every(c=>c.pass)?'LOCAL_LIMITS_MET':'LOCAL_LIMITS_NOT_MET'};
 }
 const entry=number(x,'entry',1e-8,1e9),wallet=number(x,'wallet'),scenarioPrice=number(x,'scenarioPrice',1e-8,1e9);
 if(qty<=0||!['LONG','SHORT'].includes(x.direction))throw Error('INVALID_POSITION');
 const sign=x.direction==='LONG'?1:-1,currentPnl=sign*qty*(price-entry),scenarioPnl=sign*qty*(scenarioPrice-entry),equity=wallet+currentPnl,lossFromNow=Math.max(0,currentPnl-scenarioPnl);
 return {context:{...context,contract:'LINEAR_USDT',direction:x.direction},metrics:{notional:qty*price,currentPnl,equity,scenarioPnl,scenarioEquity:wallet+scenarioPnl,lossFromNow,exposureMultiple:equity>0?qty*price/equity:null},checks:[{key:'lossBudget',pass:lossFromNow<=budget+1e-9},{key:'positiveEquity',pass:equity>0}],status:'SCENARIO_ONLY_MARGIN_NOT_VERIFIED'};
}
