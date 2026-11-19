export function fundingOptions(assets){
 return assets.flatMap((a,i)=>{
  if(a.kind!=='stable'||!String(a.asset||'').trim())return [];
  const quantity=Number(a.qty),available=Number(a.available??a.qty);
  if(!Number.isFinite(quantity)||!Number.isFinite(available)||quantity<0||available<0||available>quantity)return [];
  return [{id:'asset-'+i,asset:String(a.asset).trim().toUpperCase(),quantity,available}];
 });
}
