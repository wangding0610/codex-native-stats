'use strict';
const fs=require('node:fs'),path=require('node:path');
const {union}=require('./stats-core.cjs');
const modelTypes=new Set(['Reasoning','AgentMessage']);
const toolTypes=new Set(['CommandExecution','McpToolCall','FileChange','WebSearch']);
class SpeedSamples {
  constructor(file){
    this.file=file;this.threads={};
    try{const data=JSON.parse(fs.readFileSync(file,'utf8'));if(data.version===1&&data.threads&&typeof data.threads==='object')this.threads=Object.fromEntries(Object.entries(data.threads).filter(([,samples])=>Array.isArray(samples)));}catch{}
  }
  snapshot(threadId,stats,observations){
    const records=[...stats.responseRecords.values()];
    const prior=Array.isArray(this.threads[threadId])?this.threads[threadId]:[];
    const samples=new Map(prior.filter(s=>this.valid(s,stats)).map(s=>[s.responseId,s]));
    let changed=false;
    for(const sample of (Array.isArray(observations)?observations.slice(-24):[])){
      if(!sample||!Number.isSafeInteger(sample.startMs)||!Number.isSafeInteger(sample.observedEndMs)||sample.observedEndMs<sample.startMs||sample.observedEndMs-sample.startMs>3600000)continue;
      const first=stats.items.get(`${sample.turnId}/${sample.firstItemId}`);
      if(!first||!modelTypes.has(first.kind)||first.start!==sample.startMs||first.end<first.start)continue;
      // A usage notification must delimit exactly one response in this turn.
      const candidates=records.filter(r=>r.turnId===sample.turnId&&r.endMs>=sample.startMs&&r.endMs<=sample.observedEndMs);
      if(candidates.length!==1)continue;
      const record=candidates[0];
      if(!Number.isSafeInteger(sample.outputTokens)||sample.outputTokens<=0||record.output!==sample.outputTokens||samples.has(record.id)||first.end>record.endMs)continue;
      const items=[...stats.items.values()].filter(i=>i.turnId===record.turnId);
      const previousEnd=Math.max(stats.turns.get(record.turnId)?.start??-Infinity,...records.filter(r=>r.turnId===record.turnId&&r.endMs<record.endMs).map(r=>r.endMs));
      const model=items.filter(i=>modelTypes.has(i.kind)&&i.start>=previousEnd&&i.end<=record.endMs);
      if(model.some(i=>i.start<sample.startMs))continue;
      const tools=items.filter(i=>toolTypes.has(i.kind)).map(i=>[Math.max(sample.startMs,i.start),Math.min(record.endMs,i.end)]).filter(([a,b])=>b>a);
      const overlap=tools.flatMap(([a,b])=>model.map(i=>[Math.max(a,i.start),Math.min(b,i.end)]));
      const independentTools=union(tools)-union(overlap);
      const durationMs=record.endMs-sample.startMs-independentTools*1000;
      if(!Number.isFinite(durationMs)||durationMs<250)continue;
      const accepted={responseId:record.id,turnId:record.turnId,firstItemId:sample.firstItemId,startMs:sample.startMs,endMs:record.endMs,outputTokens:record.output,durationMs};
      samples.set(record.id,accepted);changed=true;
    }
    const sorted=[...samples.values()].sort((a,b)=>a.endMs-b.endMs).slice(-128);
    this.threads[threadId]=sorted;
    if(changed)this.save();
    const latest=sorted.at(-1),duration=sorted.reduce((n,s)=>n+s.durationMs,0),output=sorted.reduce((n,s)=>n+s.outputTokens,0);
    return {latest:latest?latest.outputTokens*1000/latest.durationMs:null,mean:duration>0?output*1000/duration:null,samples:sorted.length,latestEndMs:latest?.endMs??null,source:'official-output-events'};
  }
  valid(sample,stats){
    if(!sample||typeof sample.responseId!=='string'||!Number.isFinite(sample.durationMs)||sample.durationMs<250)return false;
    const record=stats.responseRecords.get(sample.responseId),first=stats.items.get(`${sample.turnId}/${sample.firstItemId}`);
    return !!record&&record.turnId===sample.turnId&&record.output===sample.outputTokens&&record.endMs===sample.endMs&&!!first&&first.start===sample.startMs&&modelTypes.has(first.kind);
  }
  save(){
    const recent=Object.entries(this.threads).sort((a,b)=>(b[1].at(-1)?.endMs||0)-(a[1].at(-1)?.endMs||0)).slice(0,24);
    this.threads=Object.fromEntries(recent);
    try{fs.mkdirSync(path.dirname(this.file),{recursive:true});const temp=this.file+'.'+process.pid+'.next';fs.writeFileSync(temp,JSON.stringify({version:1,threads:this.threads}));fs.renameSync(temp,this.file);}catch{}
  }
}
module.exports={SpeedSamples};
