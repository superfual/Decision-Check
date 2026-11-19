import test from 'node:test';import assert from 'node:assert/strict';
import {CONFIG,KEYS,NETLIST,readCombination,verifyReceipt,decodeBytes} from '../site/tapeout.mjs';
import {cashSafetyDraft,packCashInputs,evalNandDraft} from '../circuits/cash-safety.mjs';
const word=n=>BigInt(n).toString(16).padStart(64,'0'),abi=s=>'0x'+word(32)+word(s.length/2)+s.padEnd(Math.ceil(s.length/64)*64,'0');
const block='0x123',header={number:block,hash:'0x'+'ab'.repeat(32),timestamp:'0x123456'},nand='000000020000030000000400000400000005000005';
function mock({wrongChain=false,wrongDesign=false,reorg=false}={}){let headers=0;return async(method,params)=>{
 if(method==='eth_chainId')return wrongChain?'0x38':'0xc4';if(method==='eth_blockNumber')return block;
 if(method==='eth_getBlockByNumber')return {...header,hash:reorg&&headers++?'0x'+'cd'.repeat(32):header.hash};
 if(method==='eth_getStorageAt')return '0x'+'0'.repeat(24)+CONFIG.beacon.slice(2);
 if(method==='eth_getCode')return '0x123456';
 if(method!=='eth_call')throw Error('NO_TRANSACTIONS_ALLOWED');
 assert.equal(params[1],block);const data=params[0].data;if(data==='0x5c60da1b')return '0x'+'0'.repeat(24)+'977f217887e085d298cb3819cdad5a0ee35f29b2';
 const id=Number(BigInt('0x'+data.slice(10,74)));if(data.startsWith('0x084d60f1'))return '0x'+(id===49?[3,1,0,12]:[2,1,0,3]).map(word).join('');
 if(data.startsWith('0x3fc4be56'))return abi(wrongDesign?'00000000000000':id===49?NETLIST.slice(2):nand);
 if(data.startsWith('0x934d06ea')){const n=parseInt(data.slice(202,204),16);return abi((id===49?n===7:n!==3)?'01':'00');}throw Error('UNEXPECTED_CALL');
 };}
const source=n=>({bits:Object.fromEntries(KEYS.map((k,i)=>[k,Boolean(n&(1<<i))])),dataValid:true,inputHashes:{portfolio:'0'.repeat(64),market:'1'.repeat(64)},engine:'test'});
test('all 64 six-bit combinations compose three native AND3 calls at the same block',async()=>{for(let n=0;n<64;n++){const r=await readCombination(source(n),{read:mock()});assert.equal(r.output,Number(n===63));assert.equal(r.truthTable.length,12);assert.equal(r.stages.final.calldata.startsWith('0x934d06ea'),true);assert.equal(r.blockHash,header.hash);}});
test('receipt replay matches and detects edited content',async()=>{const r=await readCombination(source(63),{read:mock()});assert.equal((await verifyReceipt(r,{read:mock()})).status,'REPLAY_MATCH');const changed=structuredClone(r);changed.output=0;await assert.rejects(()=>verifyReceipt(changed,{read:mock()}),/CONTENT_CHANGED/);});
test('wrong network, changed design, RPC failure, reorg and invalid inputs cannot produce verified output',async()=>{for(const opts of [{wrongChain:true},{wrongDesign:true},{reorg:true}])await assert.rejects(()=>readCombination(source(63),{read:mock(opts)}));await assert.rejects(()=>readCombination(source(63),{read:async()=>{throw Error('RPC_DOWN')}}),/RPC_DOWN/);await assert.rejects(()=>readCombination({...source(63),dataValid:false},{read:mock()}),/DATA_NOT_VALID/);await assert.rejects(()=>readCombination({...source(63),bits:{...source(63).bits,wyckoff_valid:1}},{read:mock()}),/BOOLEAN/);assert.throws(()=>decodeBytes('0x'),/ABI/);});
const d=cashSafetyDraft();
test('numeric cash circuit checks cents and basis points without silently rounding',()=>{for(const [cash,nav,bps] of [[100000,473808,2000],[90000,473808,2000],[20000,100000,2000],[19999,100000,2000],[16777215,16777215,10000],[0,1,0],[0,1,10000]])assert.deepEqual(evalNandDraft(d,packCashInputs(cash,nav,bps)),[1,Number(BigInt(cash)*10000n>=BigInt(nav)*BigInt(bps))]);for(let i=0;i<80;i++){const nav=(i*7919%16777214)+1,cash=i*3571%(nav+1),bps=i*977%10001;assert.deepEqual(evalNandDraft(d,packCashInputs(cash,nav,bps)),[1,Number(BigInt(cash)*10000n>=BigInt(nav)*BigInt(bps))]);}assert.throws(()=>packCashInputs(1.1,100,20));assert.throws(()=>packCashInputs(10,0,20));assert.throws(()=>packCashInputs(1,16777216,20));});
test('numeric circuit rejects invalid raw domains even if caller bypasses packer',()=>{const pins=(cash,nav,bps)=>[...[24,24,14].flatMap((n,k)=>Array.from({length:n},(_,i)=>([cash,nav,bps][k]>>i)&1))];for(const x of [[0,0,2000],[100,50,2000],[50,100,10001]])assert.deepEqual(evalNandDraft(d,pins(...x)),[0,0]);});
