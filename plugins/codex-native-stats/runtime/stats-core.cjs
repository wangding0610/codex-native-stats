'use strict';
const fsp=require('node:fs').promises;
function union(intervals) {
  const list = intervals.filter(([a,b])=>Number.isFinite(a)&&Number.isFinite(b)&&b>=a).sort((a,b)=>a[0]-b[0]);
  let total=0,start=0,end=0,first=true;
  for(const [a,b] of list) {
    if(first){start=a;end=b;first=false;}
    else if(a<=end)end=Math.max(end,b);
    else{total+=end-start;start=a;end=b;}
  }
  return (first?0:total+end-start)/1000;
}

class Stats {
  constructor(file){this.file=file;this.offset=0;this.pending=Buffer.alloc(0);this.turns=new Map();this.items=new Map();this.responses=new Set();this.responseRecords=new Map();this.output=0;this.usage=null;this.usageSource=null;this.timestamp='';this.last=0;this.context=null;this.contextUpdatedMs=-Infinity;}
  accept(e) {
    if(e.type==='compacted'){
      const t=Date.parse(e.timestamp);
      if(Number.isFinite(t)&&t>=this.contextUpdatedMs){
        // Await the post-compaction estimate rather than retaining the old fill.
        this.context={usedTokens:null,maxTokens:this.context?.maxTokens??null,percent:null,updated:e.timestamp};this.contextUpdatedMs=t;
      }
      return;
    }
    if(!['token_usage_record','event_msg'].includes(e.type))return;
    const p=e.payload||{},ts=e.timestamp||'',t=Date.parse(ts);
    if(!Number.isFinite(t))return;
    this.last=Math.max(this.last,t);
    // Context is a separate snapshot: never derive it from cumulative usage or
    // skip token_count just because an authoritative thread total already exists.
    if(e.type==='event_msg'&&p.type==='token_count'&&p.info&&t>=this.contextUpdatedMs){
      const used=p.info.last_token_usage?.total_tokens,max=p.info.model_context_window;
      const usedTokens=Number.isSafeInteger(used)&&used>=0?used:null;
      const maxTokens=Number.isSafeInteger(max)&&max>0?max:null;
      this.context={usedTokens,maxTokens,percent:usedTokens!=null&&maxTokens!=null?Math.min(100,usedTokens/maxTokens*100):null,updated:ts};
      this.contextUpdatedMs=t;
    }
    if(e.type==='token_usage_record') {
      if(p.response_id&&!this.responses.has(p.response_id)){
        this.responses.add(p.response_id);this.output+=p.usage?.output_tokens||0;
        const u=p.usage||{};
        this.responseRecords.set(p.response_id,{id:p.response_id,turnId:p.turn_id,endMs:t,output:u.output_tokens,input:u.input_tokens,cached:u.cached_input_tokens??0,reasoning:u.reasoning_output_tokens??0});
        if(this.responseRecords.size>6000)this.responseRecords.delete(this.responseRecords.keys().next().value);
      }
      // Thread totals include inherited history. token_count can cover only a
      // runtime segment, so source priority must come before timestamp order.
      if(p.thread_token_usage&&(this.usageSource!=='thread'||ts>=this.timestamp)){
        this.usage=p.thread_token_usage;this.usageSource='thread';this.timestamp=ts;
      }
    } else if(p.type==='token_count'&&p.info?.total_token_usage&&this.usageSource!=='thread'&&ts>=this.timestamp) {
      this.usage=p.info.total_token_usage;this.usageSource='fallback';this.timestamp=ts;
    } else if(p.type==='task_started'&&p.turn_id) {
      this.turns.set(p.turn_id,{...(this.turns.get(p.turn_id)||{}),start:t});
    } else if(['task_complete','task_aborted','turn_aborted'].includes(p.type)&&p.turn_id) {
      const valid=Number.isFinite(p.time_to_first_token_ms)&&p.time_to_first_token_ms>=0&&(!Number.isFinite(p.duration_ms)||p.time_to_first_token_ms<=p.duration_ms);
      this.turns.set(p.turn_id,{...(this.turns.get(p.turn_id)||{}),id:p.turn_id,end:t,complete:p.type==='task_complete',ttftMs:valid?p.time_to_first_token_ms:null});
    } else if(p.type==='item_completed'&&p.started_at_ms!=null&&p.completed_at_ms!=null) {
      this.items.set(`${p.turn_id}/${p.item?.id}`,{turnId:p.turn_id,kind:p.item?.type,start:p.started_at_ms,end:p.completed_at_ms});
    }
  }
  async update() {
    if(this.updating)return this.updating;
    this.updating=this.read().finally(()=>{this.updating=null;});
    return this.updating;
  }
  async read() {
    const size=(await fsp.stat(this.file)).size;
    if(size<this.offset)throw new Error('rollout-truncated');
    if(size===this.offset)return;
    const handle=await fsp.open(this.file,'r');
    try {
      while(this.offset<size) {
        const buffer=Buffer.alloc(Math.min(1024*1024,size-this.offset));
        const {bytesRead}=await handle.read(buffer,0,buffer.length,this.offset);
        if(!bytesRead)break;
        this.offset+=bytesRead;
        const data=Buffer.concat([this.pending,buffer.subarray(0,bytesRead)]);
        let from=0,next;
        while((next=data.indexOf(10,from))!==-1) {
          // Most lines contain message bodies; discard them immediately after parsing.
          try{this.accept(JSON.parse(data.subarray(from,next).toString('utf8')));}catch{}
          from=next+1;
        }
        this.pending=data.subarray(from);
      }
    }finally{await handle.close();}
  }
  snapshot(running) {
    const turns=[...this.turns.values()].filter(t=>t.start!=null).sort((a,b)=>a.start-b.start);
    const elapsed=union(turns.map((t,i)=>[t.start,t.end??turns[i+1]?.start??(running?Date.now():this.last)]));
    const items=[...this.items.values()];
    const model=union(items.filter(i=>['Reasoning','AgentMessage'].includes(i.kind)).map(i=>[i.start,i.end]));
    const tools=union(items.filter(i=>['CommandExecution','McpToolCall','FileChange','WebSearch'].includes(i.kind)).map(i=>[i.start,i.end]));
    const covered=!!this.usage&&this.output===this.usage.output_tokens;
    const complete=[...this.turns.values()].filter(t=>t.complete).sort((a,b)=>a.end-b.end);
    const values=complete.filter(t=>t.ttftMs!=null),latest=complete.at(-1);
    const ttft={latestMs:latest?.ttftMs??null,latestTurnId:latest?.id??null,latestCompletedAt:latest?.end??null,meanMs:values.length?values.reduce((s,t)=>s+t.ttftMs,0)/values.length:null,samples:values.length};
    return {usage:this.usage,context:this.context,rounds:turns.length,steps:this.responses.size,elapsed,modelFragments:model,tools,historyCoverage:covered,
      throughput:covered&&elapsed>0?this.output/elapsed:null,cacheRatio:this.usage?.input_tokens?this.usage.cached_input_tokens/this.usage.input_tokens:null,ttft,updated:this.timestamp};
  }
}


module.exports={Stats,union};
