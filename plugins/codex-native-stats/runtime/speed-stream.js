(() => {
  'use strict';
  if(window.__codexStatsSpeedStream)return;
  const installedAt=Date.now(),threads=new Map();
  const uuid=/^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i;
  const modelTypes=new Set(['reasoning','agentMessage']);
  function thread(id){
    let value=threads.get(id);
    if(!value){value={group:null,samples:[],lastUsage:null};threads.set(id,value);}
    if(threads.size>24)threads.delete(threads.keys().next().value);
    return value;
  }
  const listener=event=>{
    const message=event.data;
    if(message?.type!=='mcp-notification'||message.hostId!=='local')return;
    const p=message.params||{},id=p.threadId;
    if(!uuid.test(id||'')||typeof p.turnId!=='string')return;
    const state=thread(id),method=message.method,item=p.item;
    if(method==='item/started'&&modelTypes.has(item?.type)){
      // History hydration and an item already in progress are not a new sample.
      if(!Number.isSafeInteger(p.startedAtMs)||p.startedAtMs<installedAt||p.startedAtMs>Date.now()+1000)return;
      if(state.group?.turnId!==p.turnId)state.group=null;
      state.group||={turnId:p.turnId,startMs:p.startedAtMs,firstItemId:item.id,open:new Set(),partial:false};
      state.group.open.add(item.id);
    }else if(method==='item/completed'&&modelTypes.has(item?.type)){
      const group=state.group;
      if(group?.turnId===p.turnId){if(!group.open.delete(item.id))group.partial=true;}
    }else if(method==='thread/tokenUsage/updated'){
      const signature=p.tokenUsage?.total?.outputTokens;
      if(signature===state.lastUsage)return;
      state.lastUsage=signature;
      const group=state.group;state.group=null;
      const outputTokens=p.tokenUsage?.last?.outputTokens;
      if(group?.turnId===p.turnId&&!group.partial&&!group.open.size&&Number.isSafeInteger(outputTokens)&&outputTokens>0){
        state.samples.push({turnId:p.turnId,startMs:group.startMs,firstItemId:group.firstItemId,observedEndMs:Date.now(),outputTokens});
        if(state.samples.length>24)state.samples.shift();
      }
    }else if(method==='turn/completed')state.group=null;
  };
  window.addEventListener('message',listener);
  // Only timing, IDs, and token counts are retained; never retain output text.
  window.__codexStatsSpeedStream={samples:id=>threads.get(id)?.samples.slice(-24)||[],stop:()=>window.removeEventListener('message',listener)};
})();
