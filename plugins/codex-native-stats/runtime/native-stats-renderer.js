(() => {
  'use strict';
  if(window.__codexNativeStatsInstalled)return;
  window.__codexNativeStatsInstalled=true;
  window.__codexNativeStatsVersion=17;
  const css=document.createElement('style');
  css.textContent=`
    .codex-native-stats,.nst-panel,.nst-help{--nst-bg:var(--color-background-elevated-primary-opaque,#242424);--nst-fg:var(--color-token-foreground,#ececec);--nst-muted:color-mix(in srgb,var(--nst-fg) 76%,transparent);--nst-subtle:color-mix(in srgb,var(--nst-fg) 52%,transparent);--nst-line:color-mix(in srgb,var(--nst-fg) 10%,transparent);--nst-accent:#a1b8e9;}
    :root.light .nst-panel,:root.light .nst-help{--nst-accent:#536fa9;}
    [data-native-stats-layout] > [data-native-stats-side=left]{flex:0 0 auto!important;}
    [data-native-stats-layout] > [data-native-stats-side=right]{flex:0 0 auto!important;width:auto!important;max-width:100%;margin-left:auto;}
    [data-native-stats-layout][data-native-stats-stacked=true]{flex-wrap:wrap;}
    [data-native-stats-layout][data-native-stats-stacked=true] > .codex-native-stats{order:1;flex:1 0 100%;flex-wrap:wrap;row-gap:2px;margin-left:0;overflow:visible;}
    [data-native-stats-stacked=true] .nst-trigger{max-width:100%;}
    [data-native-stats-stacked=true] .nst-trigger-label{min-width:0;white-space:normal;overflow-wrap:anywhere;}
    .codex-native-stats{box-sizing:border-box;display:flex;align-items:center;justify-content:flex-start;flex:1 1 0;min-width:0;gap:0;margin-left:4px;white-space:nowrap;overflow:hidden;color:var(--nst-muted);font-family:var(--font-sans,system-ui,'Microsoft YaHei UI',sans-serif);font-size:13px;line-height:1.4;}
    .codex-native-stats[hidden]{display:none;}
    /* A dedicated stats row makes this a two-row surface, not a single-line pill. */
    [data-codex-composer-root] [data-composer-surface-variant][data-composer-radius-variant=default]:has(>.codex-native-stats[data-placement=footer]:not([hidden])){--composer-border-radius:var(--radius-3xl,24px);border-radius:var(--composer-border-radius);}
    [data-codex-composer-root] [data-composer-surface-variant]:has(>.codex-native-stats[data-placement=footer]:not([hidden])) [data-composer-footer-responsive][data-composer-layout=single-line]{padding:8px 12px;}
    [data-codex-composer-root] [data-composer-surface-variant]:has(>.codex-native-stats[data-placement=footer]:not([hidden])) [data-composer-footer-responsive][data-composer-layout=single-line][data-composer-rows=stacked]{padding-top:0;}
    .codex-native-stats[data-placement=footer]{flex:0 0 auto;align-self:stretch;width:auto;margin:0 8px 6px;flex-wrap:wrap;row-gap:2px;overflow:visible;}
    .codex-native-stats[data-placement=footer] .nst-trigger{max-width:100%;}
    .codex-native-stats[data-placement=footer] .nst-trigger-label{min-width:0;white-space:normal;overflow-wrap:anywhere;}
    .codex-native-stats .nst-trigger{position:relative;display:inline-flex;flex:0 0 auto;align-items:center;justify-content:center;gap:7px;min-width:0;padding:3px 12px;border:0;border-radius:0;background:transparent;color:inherit;font:inherit;font-family:var(--font-sans,system-ui,'Microsoft YaHei UI',sans-serif);font-size:13px;line-height:24px;white-space:nowrap;cursor:pointer;}
    .codex-native-stats .nst-trigger::before{content:'';position:absolute;left:0;top:8px;bottom:8px;width:1px;background:var(--nst-line);}
    .codex-native-stats .nst-trigger:hover,.codex-native-stats .nst-trigger[aria-expanded=true]{color:var(--nst-fg);background:color-mix(in srgb,var(--nst-fg) 3%,transparent);}
    .codex-native-stats .nst-trigger:focus-visible,.nst-panel button:focus-visible{outline:2px solid var(--nst-accent);outline-offset:-2px;border-radius:5px;}
    .nst-timing-label{display:inline-flex;align-items:center;gap:6px;}
    .nst-speed-dot{color:var(--nst-subtle);}
    .nst-icon{display:block;width:20px;height:20px;flex:0 0 auto;stroke:currentColor;fill:none;stroke-width:1.65;stroke-linecap:round;stroke-linejoin:round;}
    .codex-native-stats .nst-icon{width:16px;height:16px;}
    .codex-native-stats[data-density=compact] .nst-trigger{font-size:12px;padding:3px 7px;gap:5px;}
    .codex-native-stats[data-density=small] .nst-trigger{font-size:12px;padding:3px 6px;gap:5px;}
    .codex-native-stats[data-density=small] .nst-speed,.codex-native-stats[data-density=small] .nst-speed-dot{display:none;}
    .nst-panel,.nst-help{box-sizing:border-box;position:fixed;margin:0;color:var(--nst-fg);background:var(--nst-bg);border:1px solid var(--nst-line);box-shadow:0 12px 36px #0004;}
    .nst-panel{display:none;flex-direction:column;width:390px;max-width:calc(100vw - 16px);max-height:calc(100vh - 16px);padding:0;border-radius:14px;overflow:hidden;container-type:inline-size;font:15px/1.5 system-ui,'Microsoft YaHei UI',sans-serif;}
    .nst-panel:popover-open{display:flex;}
    .nst-panel [hidden]{display:none!important;}
    .nst-panel button{font:inherit;border:0;cursor:pointer;}
    .nst-header{display:flex;align-items:center;gap:13px;margin:0 18px;padding:15px 0;flex:0 0 auto;border-bottom:1px solid var(--nst-line);}
    .nst-header>.nst-icon{width:22px;height:22px;color:var(--nst-accent);}
    .nst-title{margin:0;font-size:18px;line-height:1.4;font-weight:600;color:var(--nst-fg);}
    .nst-body{padding:0 18px;overflow:auto;min-height:0;scrollbar-width:thin;scrollbar-color:var(--nst-line) transparent;}
    .nst-total-time,.nst-token-total{display:flex;align-items:center;gap:12px;border-bottom:1px solid var(--nst-line);padding:12px 0;}
    .nst-label{color:var(--nst-fg);}
    .nst-value{margin-left:auto;color:var(--nst-fg);white-space:nowrap;font-size:15px;font-weight:400;font-variant-numeric:tabular-nums;}
    .nst-value.nst-missing{font-size:12px;font-weight:400;color:var(--nst-subtle);}
    .nst-section{border-bottom:1px solid var(--nst-line);padding:12px 0 11px;}
    .nst-section:last-child,.nst-section.nst-execution{border-bottom:0;}
    .nst-section-title{margin:0 0 7px;color:var(--nst-subtle);font-size:12px;line-height:1.6;font-weight:400;}
    .nst-stat-row{display:flex;align-items:center;min-height:29px;gap:10px;padding:0;}
    .nst-row-label{display:flex;align-items:center;gap:8px;color:var(--nst-muted);min-width:0;}
    .nst-info{display:inline-grid;place-items:center;padding:0;background:transparent;color:var(--nst-subtle);width:16px;height:20px;flex:0 0 auto;}
    .nst-info:hover,.nst-info:focus-visible{color:var(--nst-accent);}
    .nst-info .nst-icon{width:14px;height:14px;stroke-width:1.5;}
    .nst-footer{display:flex;align-items:center;justify-content:space-between;gap:8px;margin:0;padding:12px 18px;border-top:1px solid var(--nst-line);flex:0 0 auto;font-size:11px;line-height:1.5;color:var(--nst-subtle);}
    .nst-more{display:inline-flex;align-items:center;gap:3px;color:var(--nst-accent);background:none;padding:0;white-space:nowrap;font-size:12px!important;}
    .nst-more:hover{color:var(--nst-fg);}.nst-more .nst-icon{width:14px;height:14px;}
    .nst-advanced{padding:12px 0;border-top:1px solid var(--nst-line);}
    .nst-advanced .nst-stat-row{gap:7px;min-height:30px;}.nst-advanced .nst-value{font-size:13px;}
    .nst-advanced-note{margin:8px 0 3px;color:var(--nst-subtle);font-size:11px;line-height:1.65;}
    .nst-token-total{padding:15px 0;}
    .nst-token-number{font-variant-numeric:tabular-nums;}
    .nst-token-card{padding:16px 0;border-bottom:1px solid var(--nst-line);}
    .nst-token-card:last-child{border-bottom:0;padding:16px 0 24px;}
    .nst-context .nst-card-head{margin-bottom:8px;}
    .nst-context .nst-progress{margin:12px 0 0;}
    .nst-context-note{margin:7px 0 0;color:var(--nst-subtle);font-size:11px;line-height:1.6;}
    .nst-card-head{display:flex;align-items:center;gap:10px;color:var(--nst-fg);}
    .nst-cache-head{display:flex;align-items:center;padding:16px 0 14px;gap:7px;color:var(--nst-muted);}
    .nst-progress{height:8px;background:color-mix(in srgb,var(--nst-fg) 20%,transparent);border-radius:99px;overflow:hidden;margin:0 0 16px;}
    .nst-progress-fill{height:100%;width:0;background:var(--nst-accent);border-radius:inherit;transition:width .2s ease;}
    .nst-legend-row{display:flex;align-items:center;gap:9px;color:var(--nst-muted);padding:5px 0;}
    .nst-dot{width:10px;height:10px;border-radius:50%;flex:0 0 auto;background:var(--nst-subtle);}.nst-dot.nst-cached{background:var(--nst-accent);}
    .nst-legend-row .nst-value{color:var(--nst-muted);}
    .nst-reasoning{display:flex;align-items:center;gap:9px;padding:15px 0 0;color:var(--nst-subtle);}
    .nst-reasoning>.nst-icon{width:17px;height:17px;}
    .nst-reasoning .nst-value{color:var(--nst-muted);}
    .nst-empty{padding:22px 18px;color:var(--nst-subtle);font-size:13px;}
    .nst-help{display:none;max-width:min(300px,calc(100vw - 24px));padding:9px 12px;border-radius:9px;font:12px/1.65 system-ui,'Microsoft YaHei UI',sans-serif;color:var(--nst-muted);pointer-events:none;z-index:1;}
    .nst-help:popover-open{display:block;}
    @container(max-width:340px){
      .nst-stat-row,.nst-card-head,.nst-cache-head,.nst-legend-row,.nst-reasoning,.nst-total-time,.nst-token-total{flex-wrap:wrap;row-gap:4px;}
      .nst-row-label,.nst-legend-row>span:nth-child(2){flex:0 0 auto;max-width:100%;}
      .nst-value{max-width:100%;white-space:normal;overflow-wrap:anywhere;text-align:right;}
    }
    @media(prefers-reduced-motion:reduce){.nst-progress-fill{transition:none;}}
  `;
  document.head.append(css);
  const paths={
    clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    gauge:'<path d="M3 17a9 9 0 0 1 18 0M12 15l4-5M6 13l1 .5M8.5 8.5l.5 1M15 7.5l-.4 1M18.5 12l-1 .5"/><circle cx="12" cy="15" r="1"/>',
    database:'<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 4 16 4 16 0V5M4 12c0 4 16 4 16 0"/>',
    chart:'<path fill="currentColor" stroke="none" d="M3 16a1.6 1.6 0 0 1 3.2 0v5H3Zm6-9a1.6 1.6 0 0 1 3.2 0v14H9Zm6 4a1.6 1.6 0 0 1 3.2 0v10H15Z"/><path d="M2 21h18"/>',
    pie:'<path fill="#91b7f7" stroke="none" d="M11 2a10 10 0 1 0 11 11H11Z"/><path fill="#e5efff" stroke="none" d="M13 1v10h10A11 11 0 0 0 13 1Z"/>',
    close:'<path d="m6 6 12 12M18 6 6 18"/>',
    bolt:'<path d="m13 2-9 12h7l-1 8 10-13h-7Z"/>',
    box:'<path d="m12 2 9 5v10l-9 5-9-5V7ZM3 7l9 5 9-5M12 12v10"/>',
    layers:'<path d="m12 3 9 5-9 5-9-5ZM3 12l9 5 9-5M3 16l9 5 9-5"/>',
    refresh:'<path d="M20 8a8 8 0 0 0-14-3L3 8m0-5v5h5M4 16a8 8 0 0 0 14 3l3-3m0 5v-5h-5"/>',
    list:'<path d="M8 5h12M8 12h12M8 19h12"/><circle cx="3" cy="5" r=".8"/><circle cx="3" cy="12" r=".8"/><circle cx="3" cy="19" r=".8"/>',
    wrench:'<path d="M14 4a6 6 0 0 0-7 8L2.5 17a2.5 2.5 0 0 0 4 3l4.5-5a6 6 0 0 0 8-7l-4 4-3-3Z"/>',
    info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
    up:'<path d="M12 21V3m-7 7 7-7 7 7"/>',
    down:'<path d="M12 3v18m-7-7 7 7 7-7"/>',
    branch:'<path d="M6 3v13h14m-4-4 4 4-4 4M3 3h6"/>',
    chevron:'<path d="m9 5 7 7-7 7"/>'
  };
  const el=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!=null)n.textContent=text;return n;};
  const icon=name=>{const n=document.createElementNS('http://www.w3.org/2000/svg','svg');n.setAttribute('viewBox','0 0 24 24');n.setAttribute('class','nst-icon');n.setAttribute('aria-hidden','true');n.innerHTML=paths[name]||paths.info;return n;}; // SVG paths above are fixed application assets.
  const compact=(n,zeros=false)=>n>=1e12?(n/1e12).toFixed(1)+'T':n>=1e9?(n/1e9).toFixed(1)+'B':n>=1e6?(n/1e6).toFixed(1)+'M':n>=1e3?(n/1e3).toFixed(1).replace(zeros?/$^/:/\.0$/,'')+'k':String(n??0);
  const seconds=n=>{n=Math.floor(Math.max(0,n||0));return n>=3600?`${Math.floor(n/3600)}时 ${Math.floor(n%3600/60)}分 ${n%60}秒`:n>=60?`${Math.floor(n/60)}分 ${n%60}秒`:`${n} 秒`;};
  const speed=n=>n==null?'暂无采样':`≈${n.toFixed(1)} tok/s`;
  const latency=ms=>ms==null?'暂无记录':`${(ms/1000).toFixed(2)} 秒`;
  const clock=t=>t&&Number.isFinite(new Date(t).getTime())?new Date(t).toLocaleTimeString('zh-CN',{hour12:false}):'—';
  const stamp=t=>t&&Number.isFinite(new Date(t).getTime())?new Date(t).toLocaleString('zh-CN',{hour12:false}):'—';
  const tokens=n=>`${(n??0).toLocaleString('en-US')} tok`;
  const instances=new Map();let queued=false,serial=0;

  function install(root){
    const left=root.querySelector('[data-composer-navigation-target="permissions"]'),right=root.querySelector('[data-composer-navigation-target="reasoning"]');
    if(!left||!right)return;
    let row=left.parentElement;while(row&&row!==root&&!row.contains(right))row=row.parentElement;
    if(!row||row===root)return;
    const branch=n=>{while(n.parentElement!==row)n=n.parentElement;return n;};
    const leftBranch=branch(left),rightBranch=branch(right);if(leftBranch===rightBranch)return;
    // Fullscreen uses the native adaptive composer. Its input-width observer
    // must see only native controls: adding stats there can change its mode.
    const surface=left.closest('[data-composer-surface-variant]');
    // Async questions override the outer layout prop inside the composer.
    const modeOwner=left.closest('[data-native-stats-effective-mode]')||root;
    const composerMode=modeOwner.dataset.nativeStatsEffectiveMode||root.dataset.nativeStatsComposerMode;
    const dedicated=!!surface&&root.contains(surface);
    const bar=el('div','codex-native-stats');bar.hidden=true;root.dataset.nativeStatsEnabled='false';bar.setAttribute('aria-label','会话统计与 Token 用量');
    const triggers={};
    for(const [key,glyph,label] of [['timing','clock','会话统计'],['usage','database','Token 用量']]){
      const button=el('button','nst-trigger');button.type='button';button.dataset.view=key;button.setAttribute('aria-label',label);button.setAttribute('aria-haspopup','dialog');button.setAttribute('aria-expanded','false');
      const value=el('span','nst-trigger-label','—');button.append(icon(glyph),value);bar.append(button);triggers[key]={button,value};
    }
    const timingLabel=triggers.timing.value,roundsLabel=el('span'),speedLabel=el('span','nst-speed');
    timingLabel.classList.add('nst-timing-label');timingLabel.replaceChildren(roundsLabel,el('span','nst-speed-dot','·'),speedLabel);triggers.timing.value=roundsLabel;
    if(dedicated){bar.dataset.placement='footer';surface.append(bar);}
    else{row.insertBefore(bar,rightBranch);}
    const panel=el('div','codex-native-stats-tip nst-panel');panel.id=`native-stats-panel-${++serial}`;panel.setAttribute('popover','manual');panel.setAttribute('role','dialog');
    const help=el('div','nst-help');help.id=`native-stats-help-${serial}`;help.setAttribute('popover','manual');help.setAttribute('role','tooltip');
    for(const {button} of Object.values(triggers))button.setAttribute('aria-controls',panel.id);
    document.body.append(panel,help);
    let data=null,currentId=null,currentHost=null,busy=false,view=null,anchor=null,opened=false,leaveTimer=null,suppressFocus=false,infoAnchor=null,advanced=false,bindings={},body,empty,footer,advancedBody;
    const set=(node,value)=>{if(node&&node.textContent!==value)node.textContent=value;};
    const bind=(key,node)=>{bindings[key]=node;return node;};
    const hideHelp=()=>{try{help.hidePopover();}catch{}infoAnchor=null;};
    function showHelp(button,text){
      clearTimeout(leaveTimer);set(help,text);infoAnchor=button;
      try{help.showPopover();}catch{return;}
      const r=button.getBoundingClientRect(),b=help.getBoundingClientRect();
      help.style.left=Math.max(8,Math.min(r.left-8,innerWidth-b.width-8))+'px';
      help.style.top=(r.top-b.height-8>=8?r.top-b.height-8:Math.min(innerHeight-b.height-8,r.bottom+7))+'px';
    }
    function info(text){
      const b=el('button','nst-info');b.type='button';b.append(icon('info'));b.setAttribute('aria-label',text);b.setAttribute('aria-describedby',help.id);
      b.addEventListener('pointerenter',()=>showHelp(b,text));b.addEventListener('pointerleave',hideHelp);b.addEventListener('focus',()=>showHelp(b,text));b.addEventListener('blur',hideHelp);b.addEventListener('click',()=>showHelp(b,text));return b;
    }
    function stat(parent,glyph,label,key,description){
      const r=el('div','nst-stat-row');if(glyph)r.append(icon(glyph));
      const l=el('span','nst-row-label',label);if(description)l.append(info(description));
      r.append(l,bind(key,el('span','nst-value','—')));parent.append(r);return r;
    }
    function section(title){const s=el('section','nst-section');s.append(el('h3','nst-section-title',title));body.append(s);return s;}
    function build(kind){
      hideHelp();panel.replaceChildren();bindings={};advanced=false;view=kind;
      const head=el('header','nst-header'),title=el('h2','nst-title',kind==='usage'?'Token 用量':'会话统计');title.id=panel.id+'-title';panel.setAttribute('aria-labelledby',title.id);
      head.append(icon(kind==='usage'?'database':'chart'),title);panel.append(head);
      body=el('div','nst-body');body.addEventListener('scroll',hideHelp);empty=el('div','nst-empty','当前任务没有可用的本地统计记录。');panel.append(body,empty);
      footer=el('footer','nst-footer'+(kind==='usage'?' nst-token-footer':''));panel.append(footer);
      if(kind==='timing'){
        const total=el('div','nst-total-time');total.append(el('span','nst-label','总耗时'),bind('elapsed',el('span','nst-value')));body.append(total);
        let s=section('响应');
        stat(s,null,'首次输出（TTFT）','ttft','最近完成轮次的首 token 延迟（TTFT），包含请求前的本地准备。当前轮次完成后更新。');
        stat(s,null,'输出速度估算','latestSpeed','最近一次完整观测的模型响应：输出 Token（含推理与工具调用参数）÷ 从首个输出项开始到响应用量落盘的时长，扣除其中的独立工具执行时间。包含网络与缓冲影响，不是服务端瞬时速度。');
        s=section('模型');
        stat(s,null,'平均采样速度','meanSpeed','有效采样的输出 Token 总数 ÷ 总采样时长，加权计算。仅统计已采集且可与用量记录配对的响应，属于客户端速度估算。');
        stat(s,null,'综合吞吐','throughput','已记录输出 Token ÷ 任务总耗时，包含工具执行和等待。历史记录不完整时不计算。');
        s=section('执行');s.classList.add('nst-execution');
        stat(s,null,'轮次','rounds');stat(s,null,'步骤','steps');stat(s,null,'模型调用','calls');stat(s,null,'工具耗时（去重）','tools');
        advancedBody=el('section','nst-advanced');advancedBody.id=panel.id+'-advanced';advancedBody.hidden=true;
        stat(advancedBody,null,'TTFT 均值','meanTtft');stat(advancedBody,null,'TTFT 样本','ttftSamples');stat(advancedBody,null,'速度样本','speedSamples');stat(advancedBody,null,'模型生成片段','modelFragments');stat(advancedBody,null,'最近速度采样','sampleTime');
        advancedBody.append(bind('coverage',el('p','nst-advanced-note')));body.append(advancedBody);
        footer.append(bind('updated',el('span')));
        const more=el('button','nst-more');more.type='button';more.setAttribute('aria-expanded','false');more.setAttribute('aria-controls',advancedBody.id);
        const moreLabel=el('span',null,'高级统计');more.append(moreLabel,icon('chevron'));
        more.addEventListener('click',()=>{advanced=!advanced;advancedBody.hidden=!advanced;more.setAttribute('aria-expanded',String(advanced));set(moreLabel,advanced?'收起统计':'高级统计');position();if(advanced)advancedBody.scrollIntoView({block:'nearest'});});footer.append(more);
      }else{
        const context=el('section','nst-token-card nst-context'),contextHead=el('div','nst-card-head');
        contextHead.append(el('span',null,'上下文占用'),info('当前上下文取客户端最近记录的上下文 Token 数，包含输入与输出；最大上下文为当前任务的有效上限。输入框中尚未发送的内容不计入，累计用量不会计入这里。'),bind('contextRatio',el('span','nst-value')));context.append(contextHead);
        stat(context,null,'当前上下文','contextUsed');stat(context,null,'最大上下文','contextMax');
        const contextProgress=bind('contextProgress',el('div','nst-progress'));contextProgress.setAttribute('role','progressbar');contextProgress.setAttribute('aria-label','上下文占用比例');contextProgress.setAttribute('aria-valuemin','0');contextProgress.setAttribute('aria-valuemax','100');contextProgress.append(bind('contextFill',el('div','nst-progress-fill')));context.append(contextProgress);
        context.append(bind('contextNote',el('p','nst-context-note')));body.append(context);
        const total=el('div','nst-token-total');total.append(el('span','nst-label','累计总用量'),bind('total',el('span','nst-token-number nst-value')));body.append(total);
        const input=el('section','nst-token-card'),head=el('div','nst-card-head');head.append(el('span',null,'输入'),bind('input',el('span','nst-value')));input.append(head);
        const cache=el('div','nst-cache-head');cache.append(el('span',null,'缓存命中率'),info('缓存率 = 缓存读取 ÷ 全部输入'),bind('cacheRatio',el('span','nst-value')));input.append(cache);
        const progress=bind('progress',el('div','nst-progress'));progress.setAttribute('role','progressbar');progress.setAttribute('aria-label','输入缓存命中率');progress.setAttribute('aria-valuemin','0');progress.setAttribute('aria-valuemax','100');progress.append(bind('fill',el('div','nst-progress-fill')));input.append(progress);
        for(const [key,label,cls] of [['cached','缓存读取',' nst-cached'],['uncached','未缓存','']]){
          const r=el('div','nst-legend-row');r.append(el('span','nst-dot'+cls),el('span',null,label),bind(key,el('span','nst-value')));input.append(r);
        }
        body.append(input);
        const output=el('section','nst-token-card'),outHead=el('div','nst-card-head');outHead.append(el('span',null,'输出（含推理）'),bind('output',el('span','nst-value')));output.append(outHead);
        const reasoning=el('div','nst-reasoning'),label=el('span','nst-row-label','推理输出');label.append(info('推理 Token 已包含在输出总量中，不重复相加。'));reasoning.append(icon('branch'),label,bind('reasoning',el('span','nst-value')));output.append(reasoning);body.append(output);
        footer.append(bind('updated',el('span')),el('span',null,'模型响应完成后更新'));
      }
      updatePanel();
    }
    function value(key,text,missing=false){set(bindings[key],text);bindings[key]?.classList.toggle('nst-missing',missing);}
    function updatePanel(){
      if(!view)return;
      const available=!!data?.available&&!!data.usage;body.hidden=!available;empty.hidden=available;footer.hidden=!available;
      if(!available)return;
      set(bindings.updated,`数据更新于 ${stamp(data.updated)}`);
      if(view==='timing'){
        value('elapsed',seconds(data.elapsed));value('ttft',latency(data.ttft?.latestMs),data.ttft?.latestMs==null);
        value('latestSpeed',speed(data.generation?.latest),data.generation?.latest==null);value('meanSpeed',speed(data.generation?.mean),data.generation?.mean==null);
        value('calls',`${data.steps} 次`);value('rounds',String(data.rounds));value('steps',String(data.steps));value('tools',seconds(data.tools));
        value('meanTtft',latency(data.ttft?.meanMs));value('ttftSamples',`${data.ttft?.samples??0} 轮`);value('speedSamples',`${data.generation?.samples??0} 次`);value('modelFragments',seconds(data.modelFragments));value('throughput',data.throughput==null?'历史不完整':`${data.throughput.toFixed(1)} tok/s`);value('sampleTime',clock(data.generation?.latestEndMs));
        set(bindings.coverage,'综合吞吐包含工具和等待；模型片段不等于完整请求耗时。'+(!data.generation?.samples?(data.collection?.state==='listening'?'等待一次完整的输出事件与用量记录配对；中途打开的回复不补算。':'没有可核验的速度记录。'):'速度使用完整观测的响应，按本地用量记录核验；包含网络和缓冲影响。'));
      }else{
        const context=data.context,contextPercent=context?.percent;
        value('contextUsed',context?.usedTokens==null?'暂无记录':tokens(context.usedTokens),context?.usedTokens==null);
        value('contextMax',context?.maxTokens==null?'暂无记录':tokens(context.maxTokens),context?.maxTokens==null);
        value('contextRatio',contextPercent==null?'—':contextPercent.toFixed(1)+'%',contextPercent==null);
        bindings.contextFill.style.width=(contextPercent??0)+'%';
        bindings.contextProgress.setAttribute('aria-valuetext',contextPercent==null?'暂无上下文占用记录':contextPercent.toFixed(1)+'%');
        if(contextPercent==null)bindings.contextProgress.removeAttribute('aria-valuenow');else bindings.contextProgress.setAttribute('aria-valuenow',String(contextPercent));
        set(bindings.contextNote,context?.usedTokens==null?'等待新的上下文记录':`随响应更新；压缩后会降低 · ${clock(context.updated)}`);
        const u=data.usage,ratio=data.cacheRatio==null?null:Math.max(0,Math.min(1,data.cacheRatio)),percent=ratio==null?'—':Math.round(ratio*100)+'%';
        value('total',tokens(u.total_tokens));
        value('input',tokens(u.input_tokens));value('output',tokens(u.output_tokens));value('reasoning',tokens(u.reasoning_output_tokens));
        value('cacheRatio',percent);value('cached',tokens(u.cached_input_tokens)+' · '+percent);value('uncached',tokens(Math.max(0,u.input_tokens-u.cached_input_tokens))+' · '+(ratio==null?'—':(100-Math.round(ratio*100))+'%'));
        bindings.fill.style.width=((ratio??0)*100)+'%';bindings.progress.setAttribute('aria-valuetext',ratio==null?'无输入用量':percent);
        if(ratio==null)bindings.progress.removeAttribute('aria-valuenow');else bindings.progress.setAttribute('aria-valuenow',String(Math.round(ratio*100)));
      }
      if(opened)position();
    }
    function position(){
      if(!opened||!anchor)return;
      const r=anchor.getBoundingClientRect(),b=panel.getBoundingClientRect();
      panel.style.left=Math.max(8,Math.min(r.left,innerWidth-b.width-8))+'px';
      const above=r.top-b.height-10;
      panel.style.top=Math.max(8,above>=8?above:Math.min(r.bottom+8,innerHeight-b.height-8))+'px';
      if(infoAnchor)showHelp(infoAnchor,help.textContent);
    }
    function show(kind,button){
      if(bar.hidden)return;
      clearTimeout(leaveTimer);
      anchor=button;if(view!==kind)build(kind);else updatePanel();
      try{panel.showPopover();}catch{return;}opened=true;
      for(const {button:b} of Object.values(triggers))b.setAttribute('aria-expanded',String(b===anchor));position();
    }
    function hide(restore=false){
      clearTimeout(leaveTimer);hideHelp();try{panel.hidePopover();}catch{}opened=false;
      for(const {button} of Object.values(triggers))button.setAttribute('aria-expanded','false');
      if(restore&&anchor?.isConnected){suppressFocus=true;anchor.focus({preventScroll:true});suppressFocus=false;}
    }
    function delayedHide(){clearTimeout(leaveTimer);leaveTimer=setTimeout(()=>{if(!panel.matches(':hover')&&!bar.matches(':hover'))hide();},180);}
    for(const [key,{button}] of Object.entries(triggers)){
      const kind=key==='usage'?'usage':'timing';
      button.addEventListener('pointerenter',()=>show(kind,button));button.addEventListener('pointerleave',delayedHide);
      button.addEventListener('focus',()=>{if(!suppressFocus&&button.matches(':focus-visible'))show(kind,button);});button.addEventListener('blur',delayedHide);
    }
    panel.addEventListener('pointerenter',()=>clearTimeout(leaveTimer));panel.addEventListener('pointerleave',delayedHide);
    panel.addEventListener('focusin',()=>clearTimeout(leaveTimer));panel.addEventListener('focusout',delayedHide);
    const escape=e=>{if(e.key==='Escape'&&opened){e.preventDefault();e.stopPropagation();hide(true);}};
    const outside=e=>{if(opened&&!panel.contains(e.target)&&!bar.contains(e.target))hide();};
    document.addEventListener('keydown',escape,true);document.addEventListener('pointerdown',outside,true);window.addEventListener('resize',position);
    let layoutFrame=0;
    function layout(){
      if(bar.hidden||!bar.isConnected)return;
      if(dedicated){bar.dataset.density='normal';return;}
      const style=getComputedStyle(row),gap=parseFloat(style.columnGap)||0;
      const siblings=[...row.children].filter(n=>n!==bar&&getComputedStyle(n).display!=='none');
      // Measure the controls, not the native trailing wrapper's former full width.
      // Automatic margins contain free space and must not reduce this budget.
      const rowWidth=row.clientWidth-(parseFloat(style.paddingLeft)||0)-(parseFloat(style.paddingRight)||0);
      const available=rowWidth-siblings.reduce((n,node)=>n+node.getBoundingClientRect().width,0)-gap*siblings.length-4;
      const required={};
      for(const mode of ['normal','compact','small']){
        bar.dataset.density=mode;
        required[mode]=Math.ceil(Object.values(triggers).reduce((n,{button})=>n+button.getBoundingClientRect().width,0));
      }
      const stacked=available<required.small+2;
      row.dataset.nativeStatsStacked=String(stacked);
      const budget=stacked?rowWidth:available;
      bar.dataset.density=budget>=required.normal+2?'normal':budget>=required.compact+2?'compact':'small';
    }
    const queueLayout=()=>{if(!layoutFrame)layoutFrame=requestAnimationFrame(()=>{layoutFrame=0;layout();position();});};
    const resize=new ResizeObserver(queueLayout);for(const node of (dedicated?[surface,bar]:[row,bar,leftBranch,rightBranch]))resize.observe(node);
    document.fonts?.ready.then(()=>{if(bar.isConnected)queueLayout();});
    function updateBar(){
      const enabled=!!currentId&&!!data&&data.enabled!==false;
      root.dataset.nativeStatsEnabled=String(enabled);bar.hidden=!enabled;
      if(!enabled){
        hide();if(!dedicated){delete row.dataset.nativeStatsLayout;delete row.dataset.nativeStatsStacked;delete leftBranch.dataset.nativeStatsSide;delete rightBranch.dataset.nativeStatsSide;}
        return;
      }
      if(!dedicated){row.dataset.nativeStatsLayout='true';leftBranch.dataset.nativeStatsSide='left';rightBranch.dataset.nativeStatsSide='right';}
      const available=!!data?.available&&!!data.usage;
      set(triggers.timing.value,available?`${data.rounds} 轮 · ${data.steps} 步`:'统计 —');
      set(speedLabel,available&&data.generation?.latest!=null?`≈ ${data.generation.latest.toFixed(1)} tok/s`:'等待采集');
      set(triggers.usage.value,available?`${compact(data.usage.total_tokens,true)} tokens`:'用量暂不可用');
      triggers.timing.button.setAttribute('aria-label',available?`会话统计，${data.rounds}轮，${data.steps}步，客户端生成速度估算 ${speed(data.generation?.latest)}`:'会话统计');
      triggers.usage.button.setAttribute('aria-label',available?`Token 用量，${data.usage.total_tokens.toLocaleString('en-US')} tokens`:'Token 用量暂无数据');
      updatePanel();
      queueLayout();
    }
    async function refresh(){
      const id=root.getAttribute('data-native-stats-thread'),host=root.getAttribute('data-native-stats-host')||'local';
      if(id!==currentId||host!==currentHost){data=null;currentId=id;currentHost=host;hide();updateBar();}
      if(!id){bar.hidden=true;return;}if(busy)return;busy=true;
      try{
        const result=await window.codexNativeStats?.getStats({threadId:id,hostId:host,running:root.getAttribute('data-native-stats-running')==='true'});
        if(root.getAttribute('data-native-stats-thread')!==id||(root.getAttribute('data-native-stats-host')||'local')!==host)return;
        data=result;updateBar();
      }catch{data=null;updateBar();}finally{busy=false;}
    }
    const interval=setInterval(refresh,1200);
    instances.set(root,{bar,refresh,attached:()=>left.isConnected&&right.isConnected&&root.querySelector('[data-composer-navigation-target="permissions"]')===left&&root.querySelector('[data-composer-navigation-target="reasoning"]')===right&&(left.closest('[data-native-stats-effective-mode]')||root)===modeOwner&&(modeOwner.dataset.nativeStatsEffectiveMode||root.dataset.nativeStatsComposerMode)===composerMode&&bar.parentElement===(dedicated?surface:row),destroy(){clearInterval(interval);resize.disconnect();cancelAnimationFrame(layoutFrame);hide();document.removeEventListener('keydown',escape,true);document.removeEventListener('pointerdown',outside,true);window.removeEventListener('resize',position);bar.remove();panel.remove();help.remove();if(!dedicated){delete row.dataset.nativeStatsLayout;delete row.dataset.nativeStatsStacked;delete leftBranch.dataset.nativeStatsSide;delete rightBranch.dataset.nativeStatsSide;}}});refresh();
  }
  function reconcile(){queued=false;for(const [root,i] of instances)if(!root.isConnected||!i.bar.isConnected||!i.attached()){i.destroy();instances.delete(root);}for(const root of document.querySelectorAll('[data-codex-composer-root][data-native-stats-thread]'))if(!instances.has(root))install(root);}
  new MutationObserver(records=>{
    for(const r of records)if(r.type==='attributes')instances.get(r.target)?.refresh();
    if(!records.some(r=>r.type==='attributes'||![...r.addedNodes,...r.removedNodes].every(n=>n.nodeType===3)))return;
    if(!queued){queued=true;requestAnimationFrame(reconcile);}
  }).observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:['data-native-stats-thread','data-native-stats-host','data-native-stats-composer-mode','data-native-stats-effective-mode']});
  reconcile();
})();
