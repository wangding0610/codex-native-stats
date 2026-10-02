(() => {
  'use strict';
  const token=__STATS_BINDING_TOKEN__,previous=window.__codexStatsOfficialTransport;
  if(previous?.token===token)return;
  previous?.dispose();
  const pending=new Map();let serial=0;
  window.__codexStatsOfficialTransport={token,dispose(){for(const p of pending.values()){clearTimeout(p.timer);p.resolve({enabled:true,available:false,reason:'adapter-reconnecting'});}pending.clear();}};
  window.__codexStatsResolve=(id,result)=>{const p=pending.get(id);if(p){clearTimeout(p.timer);pending.delete(id);p.resolve(result);}};
  window.codexNativeStats={getStats:request=>new Promise(resolve=>{
    const id=++serial,timer=setTimeout(()=>{pending.delete(id);resolve({enabled:false,available:false,reason:'adapter-unavailable'});},10000);
    const streamSamples=window.__codexStatsSpeedStream?.samples(request.threadId)||[];
    pending.set(id,{resolve,timer});window.__codexStatsBinding(JSON.stringify({id,token,request:{...request,streamSamples}}));
  })};
  if(window.__codexStatsOfficialBridge)return;
  window.__codexStatsOfficialBridge=true;
  const uuid=/^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i;
  function normalizeThreadId(value){
    if(typeof value!=='string')return '';
    const plain=value.replace(/^local:/i,'');return uuid.test(plain)?plain:'';
  }
  function scopeData(root){
    const key=Object.keys(root).find(k=>k.startsWith('__reactFiber$'));let fiber=key&&root[key],running=false;
    for(let depth=0;fiber&&depth<60;depth++,fiber=fiber.return){
      const props=fiber.memoizedProps;
      if(props&&typeof props.isResponseInProgress==='boolean')running=props.isResponseInProgress;
      const lists=fiber.updateQueue?.memoCache?.data;
      if(lists)for(const list of lists)for(const item of list){
        try{
          const value=item?.value;
          if(!value||!['local','remote','new'].includes(value.kind))continue;
          if(value.kind==='new'&&('browserTabMentionConversationId' in value||'routeConversationId' in value))return {id:'',host:'local',kind:'new',running};
          const id=[value.conversationId,value.routeConversationId,value.clientThreadId].map(normalizeThreadId).find(Boolean);
          if(id)return {id,host:value.kind==='local'?'local':'remote',kind:value.kind,running};
        }catch{}
      }
    }
    return null;
  }
  function routeData(){
    const match=(location.pathname+location.hash).match(/\/(local|remote|hotkey-window\/thread)\/([0-9a-f-]{36})(?:[/?#]|$)/i);
    return match&&uuid.test(match[2])?{id:match[2],host:match[1]==='remote'?'remote':'local',kind:match[1]==='remote'?'remote':'local',running:false}:null;
  }
  const assign=(root,key,value)=>{if(root.getAttribute(key)!==value)root.setAttribute(key,value);};
  function refresh(){
    for(const root of document.querySelectorAll('[data-codex-composer-root]')){
      const data=scopeData(root)||routeData();
      assign(root,'data-native-stats-thread',data?.id||'');assign(root,'data-native-stats-host',data?.host||'local');
      assign(root,'data-native-stats-identity-kind',data?.kind||'unknown');
      const stopping=!!root.querySelector('[aria-label="停止"],[aria-label="Stop"],[data-composer-navigation-target="stop"]');
      assign(root,'data-native-stats-running',String(!!data?.running||stopping));assign(root,'data-native-stats-composer-mode','plugin-footer');
    }
  }
  let scheduled=false;
  new MutationObserver(()=>{if(!scheduled){scheduled=true;requestAnimationFrame(()=>{scheduled=false;refresh();});}}).observe(document.documentElement,{subtree:true,childList:true});
  setInterval(refresh,250);refresh();
})();
