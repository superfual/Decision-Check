// Ephemeral, same-tab workflow handoff. This is not an authentication boundary.
export const HANDOFF_KEY='decision-check.portfolio-handoff.v1';
export function createHandoff(record,now=Date.now()){
 if(record?.input?.schema!=='portfolio-insider.input.v1'||record?.report?.status!=='ANALYTICAL_REVIEW_ONLY')throw Error('PORTFOLIO_ANALYSIS_REQUIRED');
 const d=record.input.decision;
 if(!d||!['SPOT','LINEAR_FUTURES'].includes(d.product)||!['CYCLE','SWING','INTRADAY'].includes(d.profile)||d.symbol!==d.asset+'USDT')throw Error('INVALID_DECISION_SCOPE');
 return {schema:'decision-check.handoff.v1',createdAt:now,record};
}
export function readHandoff(raw,now=Date.now()){
 try{const x=JSON.parse(raw);if(x.schema!=='decision-check.handoff.v1'||!Number.isFinite(x.createdAt)||x.createdAt>now||now-x.createdAt>30*60*1000)return null;createHandoff(x.record,now);return x.record;}catch{return null;}
}
