// UI adapter only. Authoritative risk checks still run in the Python brain.
const n=(v,key,min=0)=>{if(v===''||v===null||v===undefined||typeof v==='boolean')throw Error('MISSING_'+key);const x=Number(v);if(!Number.isFinite(x)||x<min||x>1e12)throw Error('INVALID_'+key);return x;};
const signed=(v,key)=>{const x=Number(v);if(!Number.isFinite(x)||Math.abs(x)>1e12)throw Error('INVALID_'+key);return x;};
const money=v=>Number(v).toFixed(12).replace(/0+$/,'').replace(/\.$/,'')||'0';
const asset=v=>{const s=String(v).trim().toUpperCase();if(!/^[A-Z0-9][A-Z0-9._-]{0,19}$/.test(s))throw Error('INVALID_ASSET');return s;};
export function acceptedLossPrice(base,pct,direction='LONG'){
 const b=n(base,'cost_or_entry',1e-12),r=n(pct,'maximum_loss_pct');
 if(r<=0||r>=100)throw Error('LOSS_PERCENT_MUST_BE_BETWEEN_0_AND_100');
 if(!['LONG','SHORT'].includes(direction))throw Error('INVALID_DIRECTION');
 return b*(1+(direction==='SHORT'?1:-1)*r/100);
}
export function describePortfolio(m){
 let value=0,pnl=0,realized=0,margin=0;const seen=new Set();const assets=m.assets.map((r,i)=>{const a=asset(r.asset),venue=String(r.venue||'').trim();if(!venue)throw Error('MISSING_VENUE');const key=a+'@'+venue;if(seen.has(key))throw Error('DUPLICATE_ASSET_VENUE');seen.add(key);const qty=n(r.qty,'quantity'),price=n(r.price,'price',1e-12),avg=n(r.avg,'average_cost');const u=qty*(price-avg);value+=qty*price;pnl+=u;realized+=signed(r.realized||0,'realized');const available=n(r.available??qty,'available_quantity');if(available>qty)throw Error('AVAILABLE_EXCEEDS_QUANTITY');return {id:'asset-'+i,asset:a,venue,qty,available,price,avg,value:qty*price,pnl:u,realized:signed(r.realized||0,'realized'),kind:r.kind,cycle:r.cycle,lossPct:r.lossPct};});
 const positions=m.positions.map((r,i)=>{const a=asset(r.asset),qty=n(r.qty,'quantity',1e-12),entry=n(r.entry,'entry',1e-12),mark=n(r.mark,'mark',1e-12);if(!['LONG','SHORT'].includes(r.direction))throw Error('INVALID_DIRECTION');const u=(r.direction==='LONG'?1:-1)*qty*(mark-entry),locked=n(r.margin,'margin');pnl+=u;margin+=locked;realized+=signed(r.realized||0,'realized');return {id:'future-'+i,asset:a,qty,entry,mark,direction:r.direction,pnl:u,margin:locked,cycle:r.cycle,lossPct:r.lossPct,realized:signed(r.realized||0,'realized')};});
 const futuresPnl=positions.reduce((a,r)=>a+r.pnl,0),wallet=m.hasFutures?n(m.wallet,'futures_wallet'):0,available=m.hasFutures?n(m.available,'available_margin'):0;
 if(!m.hasFutures&&positions.length)throw Error('FUTURES_ACCOUNT_REQUIRED');
 const futuresEquity=wallet+futuresPnl,nav=value+futuresEquity;
 if(nav<=0)throw Error('NONPOSITIVE_NAV');
 if(m.hasFutures&&(available>Math.max(0,futuresEquity)+1e-8||margin>Math.max(0,futuresEquity)+1e-8))throw Error('MARGIN_EXCEEDS_EQUITY');
 const declared=m.total===''||m.total===null||m.total===undefined?null:n(m.total,'reported_total');
 return {assets,positions,nav,pnl,realized,futuresPnl,futuresEquity,wallet,available,margin,
  longCount:positions.filter(x=>x.direction==='LONG').length,shortCount:positions.filter(x=>x.direction==='SHORT').length,
  stableValue:assets.filter(x=>x.kind==='stable').reduce((a,x)=>a+x.value,0),
  reconciliationDifference:declared===null?null:declared-nav};
}
export function buildPortfolioInput(m,p){
 const c=describePortfolio(m);if(c.reconciliationDifference!==null&&Math.abs(c.reconciliationDifference)>.01)throw Error('TOTAL_DOES_NOT_MATCH_HOLDINGS');
 const target=asset(p.asset),venue=String(p.venue||'').trim(),entry=n(p.entry,'plan_entry',1e-12);
 const holding=p.product==='SPOT'?c.assets.find(r=>r.kind==='spot'&&r.asset===target&&r.venue===venue):c.positions.find(r=>r.asset===target&&m.futuresVenue===venue&&r.direction===p.direction);
 const costBase=holding?(p.product==='SPOT'?holding.avg:holding.entry):entry;
 const cyclePrice=p.cycleLossPct===undefined?n(p.cyclePrice,'plan_cycle',1e-12):acceptedLossPrice(costBase,p.cycleLossPct,p.product==='LINEAR_FUTURES'?p.direction:'LONG');
 if(!venue)throw Error('MISSING_VENUE');if(!['SPOT','LINEAR_FUTURES'].includes(p.product))throw Error('UNSUPPORTED_PRODUCT');
 const cash=[],spot=[],futures=[],prices={};
 for(const r of c.assets){if(r.kind==='stable'){cash.push({id:r.id,asset:r.asset,amount:money(r.qty),available_amount:money(r.available),fx_rate:money(r.price)});}else if(r.kind==='spot'){
   spot.push({id:r.id,asset:r.asset,venue:r.venue,quantity:money(r.qty),price:money(r.price),cost_basis:money(r.qty*r.avg)});const cut=r.lossPct===undefined?n(r.cycle,'holding_cycle_price',1e-12):acceptedLossPrice(r.avg,r.lossPct);if(r.lossPct!==undefined&&r.price<=cut)throw Error('CUT_LOSS_THRESHOLD_ALREADY_REACHED:'+r.asset);prices[r.id]=money(cut);
 }else throw Error('INVALID_ASSET_KIND');}
 for(const r of c.positions){futures.push({id:r.id,account_id:'futures-account',asset:r.asset,venue:m.futuresVenue,contract_type:'LINEAR',direction:r.direction,quantity:money(r.qty),entry_price:money(r.entry),mark_price:money(r.mark)});const cut=r.lossPct===undefined?n(r.cycle,'position_cycle_price',1e-12):acceptedLossPrice(r.entry,r.lossPct,r.direction);if(r.lossPct!==undefined&&(r.direction==='LONG'?r.mark<=cut:r.mark>=cut))throw Error('CUT_LOSS_THRESHOLD_ALREADY_REACHED:'+r.asset);prices[r.id]=money(cut);}
 const old=p.product==='SPOT'?spot.find(r=>r.asset===target&&r.venue===venue):futures.find(r=>r.asset===target&&r.venue===venue&&r.direction===p.direction);
 if(old&&((p.entryMode!=='LIMIT'&&Number(old.price??old.mark_price)!==entry)||Number(prices[old.id])!==cyclePrice))throw Error('MATCH_EXISTING_REFERENCE_AND_CYCLE_PRICE');
 if(p.product==='SPOT'&&!cash.some(r=>r.id===p.funding))throw Error('SELECT_STABLECOIN_FUNDING');
 if(p.product==='LINEAR_FUTURES'&&(!m.hasFutures||m.futuresVenue!==venue))throw Error('FUTURES_ACCOUNT_VENUE_MISMATCH');
 const input={schema:'portfolio-insider.input.v1',as_of:p.asOf||new Date().toISOString(),reporting_currency:'USD',data_source:'SELF_REPORTED',
 portfolio:{cash,spot,futures_accounts:m.hasFutures?[{id:'futures-account',settlement_asset:'USDT',wallet_balance:money(c.wallet),available_margin:money(c.available),fx_rate:'1'}]:[],futures},
 decision:{product:p.product,intent:p.product==='SPOT'?(old?'ADD_SPOT':'BUY_SPOT'):(old?'ADD_FUTURES':'OPEN_FUTURES'),asset:target,symbol:target+'USDT',venue,position_id:old?.id||null,funding_id:p.product==='SPOT'?p.funding:'futures-account',profile:p.profile,holding_horizon:p.horizon,proposed_amount:money(n(p.amount,'proposed_amount',.01)),loss_tolerance_pct:money(n(p.risk,'decision_risk')),entry_price:money(entry),entry_mode:p.entryMode||'MARKET',stop_or_scenario_price:money(n(p.stop,'stop')),cycle_price:money(cyclePrice),minimum_available_cash:money(n(p.reserve,'reserve')),direction:p.direction,leverage:money(n(p.leverage,'leverage',1))},
 cycle:{anchor_id:'manual-cycle',anchor_as_of:p.anchorTime,anchor_nav:money(n(p.anchor,'cycle_anchor',.01)),max_loss_pct:money(n(p.cycleRisk,'cycle_risk')),external_flows_reconciled:p.flows===true,prices},
 manual_context:{accounting:'Snapshot, not transaction-ledger reconciliation',input_precision:'UI adapter rounds to 12 decimal places',declared_total:m.total||null,realized_pnl_memo:money(c.realized),position_margin_memo:money(c.margin),realized_and_margin_not_added_to_nav:true}};
 return {input,summary:c};
}
