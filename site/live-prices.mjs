// Public market prices only. No account or portfolio data is sent.
export function quoteRequest({asset,venue,futures=false,stable=false}){
 const a=String(asset).trim().toUpperCase(),v=String(venue).trim().toUpperCase();
 if(!/^[A-Z0-9]{1,20}$/.test(a))throw Error('INVALID_ASSET');
 if(!futures&&a==='USD')return {fixed:true,price:'1',source:'USD'};
 // USDT is the reporting quote; do not request an invalid USDT/USDT pair.
 if(!futures&&a==='USDT')return {fixed:true,price:'1',source:'USDT = USD · accounting assumption'};
 if(v==='BINANCE')return {url:futures?'https://fapi.binance.com/fapi/v1/premiumIndex?symbol='+a+'USDT':'https://data-api.binance.vision/api/v3/ticker/price?symbol='+a+'USDT',venue:v,asset:a,futures,source:futures?'Binance USDT Futures · Mark Price':'Binance Spot · '+a+'/USDT'};
 if(v==='OKX'&&!futures)return {url:'https://www.okx.com/api/v5/market/ticker?instId='+a+'-USDT',venue:v,asset:a,futures:false,source:'OKX Spot · '+a+'/USDT'};
 // No silent swap to a different venue or unsupported derivatives contract.
 throw Error('UNSUPPORTED_PRICE_SOURCE');
}
export function parseQuote(request,data,now=Date.now()){
 let p,ts=now;
 if(request.fixed)p=request.price;
 else if(request.venue==='BINANCE'){
  if(data.symbol!==request.asset+'USDT')throw Error('SYMBOL_MISMATCH');
  p=request.futures?data.markPrice:data.price;if(request.futures)ts=Number(data.time);
 }else{
  const d=data.data?.[0];if(data.code!=='0'||d?.instId!==request.asset+'-USDT')throw Error('SYMBOL_MISMATCH');p=d.last;ts=Number(d.ts);
 }
 if(!Number.isFinite(Number(p))||Number(p)<=0||!Number.isFinite(ts)||now-ts>60000||ts>now+10000)throw Error('INVALID_OR_STALE_PRICE');
 return {price:String(p),asOf:new Date(ts).toISOString(),source:request.source};
}
export async function fetchQuote(input,fetcher=fetch){
 const r=quoteRequest(input);if(r.fixed)return parseQuote(r,{});
 const response=await fetcher(r.url,{signal:AbortSignal.timeout(8000),cache:'no-store'});
 if(!response.ok)throw Error('PRICE_HTTP_'+response.status);
 return parseQuote(r,await response.json());
}
