import test from 'node:test';
import assert from 'node:assert/strict';
import {holdingPreview,portfolioPreview} from '../site/portfolio-preview.mjs';
test('BNB screenshot values recalculate PnL, percentage and cut price',()=>{const x=holdingPreview({qty:'6',avg:'635',price:'577.26',lossPct:'50'});assert.ok(Math.abs(x.pnl+346.44)<1e-8);assert.ok(Math.abs(x.pct+9.0929133858)<1e-8);assert.equal(x.cut,317.5);assert.ok(Math.abs(x.value-3463.56)<1e-8);});
test('invalid or cleared inputs erase row results rather than retain sample results',()=>{assert.equal(holdingPreview({qty:'',avg:'635',price:'577.26'}),null);assert.equal(holdingPreview({qty:'6',avg:'',price:'577.26'}),null);});
test('an unfinished second asset does not prevent completed BNB subtotal',()=>{const x=portfolioPreview({assets:[{asset:'BNB',qty:'6',avg:'635',price:'577.26'},{asset:'',qty:'0',price:'1'}],hasFutures:false});assert.ok(Math.abs(x.nav-3463.56)<1e-8);assert.equal(x.incomplete,1);});
test('NAV follows live price and stablecoin balances',()=>{const m={assets:[{asset:'BNB',qty:'6',avg:'635',price:'577.26'},{asset:'USDT',qty:'1200',avg:'1',price:'1'}],hasFutures:false};assert.ok(Math.abs(portfolioPreview(m).nav-4663.56)<1e-8);m.assets[0].price='600';assert.equal(portfolioPreview(m).nav,4800);});
test('futures equity adds wallet and directional PnL without adding margin again',()=>{const r={qty:'1',entry:'600',mark:'500',margin:'100',lossPct:'50',direction:'SHORT'};assert.equal(holdingPreview(r,true).pnl,100);assert.equal(holdingPreview(r,true).cut,900);assert.equal(portfolioPreview({assets:[],hasFutures:true,wallet:'1000',positions:[r]}).nav,1100);r.direction='LONG';assert.equal(holdingPreview(r,true).pnl,-100);assert.equal(portfolioPreview({assets:[],hasFutures:true,wallet:'1000',positions:[r]}).nav,900);});

test('whole-NAV BNB threshold preserves cash instead of halving average cost',async()=>{
 const {portfolioLossThreshold}=await import('../site/portfolio-preview.mjs');
 const m={assets:[{kind:'spot',asset:'BNB',qty:'6',avg:'635',price:'590.72'},{kind:'stable',asset:'USDT',qty:'1200',avg:'1',price:'1'}],hasFutures:false};
 const x=portfolioLossThreshold(m,0,'50');assert.ok(Math.abs(x.price-195.36)<1e-8);assert.ok(Math.abs(6*x.price+1200-x.nav*.5)<1e-8);assert.notEqual(x.price,317.5);
 m.assets[0].avg='100';assert.equal(portfolioLossThreshold(m,0,'50').price,x.price);
 m.assets[1].qty='2000';assert.ok(portfolioLossThreshold(m,0,'50').price<x.price);
});
test('portfolio boundary never fabricates negative asset prices or ignores missing balances',async()=>{
 const {portfolioLossThreshold}=await import('../site/portfolio-preview.mjs');
 const m={assets:[{kind:'spot',asset:'BNB',qty:'1',avg:'635',price:'600'},{kind:'stable',asset:'USDC',qty:'1200',avg:'1',price:'1'}],hasFutures:false};
 assert.equal(portfolioLossThreshold(m,0,'50').reachable,false);assert.equal(portfolioLossThreshold(m,0,'50').price,null);
 m.assets[1].qty='';assert.equal(portfolioLossThreshold(m,0,'50'),null);
});
test('multiple-coin boundary holds other coins fixed and refreshes with market price',async()=>{
 const {portfolioLossThreshold}=await import('../site/portfolio-preview.mjs');
 const m={assets:[{kind:'spot',asset:'BNB',qty:'6',avg:'635',price:'600'},{kind:'spot',asset:'BTC',qty:'.01',avg:'70000',price:'80000'},{kind:'stable',asset:'USDT',qty:'1200',avg:'1',price:'1'}],hasFutures:false};
 const x=portfolioLossThreshold(m,0,'50');assert.equal(6*x.price+800+1200,5600*.5);
 m.assets[0].price='700';assert.equal(6*portfolioLossThreshold(m,0,'50').price+800+1200,6200*.5);
});
