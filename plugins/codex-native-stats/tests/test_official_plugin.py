"""Official executable, isolated local records, renderer binding and switch regression."""
from pathlib import Path
import ctypes,json,os,sqlite3,subprocess,sys,time,urllib.request,hashlib

PLUGIN=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('CODEX_STATS_TEST_OUT', str(Path.home()/'CodexStatsValidation/release-integration')));OUT.mkdir(parents=True,exist_ok=True)
HOME=OUT/'codex-home';HOME.mkdir(exist_ok=True)
os.environ['CODEX_HOME']=str(HOME);os.environ['CODEX_STATS_PLUGIN_STATE']=str(OUT/'state')
sys.path.insert(0,str(PLUGIN/'runtime'))
from official_adapter import UsageWorker,CDP,TargetAdapter
from official_adapter import installed_app
APP=installed_app().parent
BROWSER=OUT/'browser'
ID='11111111-1111-4111-8111-111111111111';OTHER='22222222-2222-4222-8222-222222222222'
def switch(on):
    (HOME/'config.toml').write_text('[plugins."codex-native-stats@codex-stats"]\nenabled = '+str(on).lower()+'\n',encoding='utf-8')
def stamp(seconds):return '2026-10-01T00:00:'+str(seconds).zfill(2)+'.000Z'
full={'input_tokens':53234086,'cached_input_tokens':50584320,'output_tokens':327697,'reasoning_output_tokens':116929,'total_tokens':53561783}
events=[{'type':'event_msg','timestamp':stamp(0),'payload':{'type':'task_started','turn_id':'one'}},
        {'type':'token_usage_record','timestamp':stamp(2),'payload':{'response_id':'r1','turn_id':'one','usage':{'output_tokens':327697},'thread_token_usage':full}},
        {'type':'event_msg','timestamp':stamp(3),'payload':{'type':'token_count','info':{'total_token_usage':{'total_tokens':1275739},'last_token_usage':{'total_tokens':94667},'model_context_window':258400}}},
        {'type':'event_msg','timestamp':stamp(4),'payload':{'type':'task_complete','turn_id':'one','duration_ms':4000,'time_to_first_token_ms':650}}]
rollout=HOME/'session.jsonl';rollout.write_text('\n'.join(json.dumps(e) for e in events)+'\n',encoding='utf-8')
db=sqlite3.connect(HOME/'state_5.sqlite');db.execute('CREATE TABLE IF NOT EXISTS threads(id TEXT PRIMARY KEY,rollout_path TEXT)');db.execute('INSERT OR REPLACE INTO threads VALUES(?,?)',(ID,str(rollout)));db.commit();db.close();switch(True)
report={'officialExecutable':str(APP/'ChatGPT.exe'),'cases':[],'checks':{},'limitations':['Question card and model/permission controls are local fixtures using the official renderer runtime; account services are not used.'],'sourceSha256':hashlib.sha256((PLUGIN/'runtime/native-stats-renderer.js').read_bytes()).hexdigest()}
p=None;adapter=None;worker=None
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def window_display(pid,show):
    callback=ctypes.WINFUNCTYPE(ctypes.c_bool,ctypes.c_void_p,ctypes.c_void_p)
    def visit(hwnd,_):
        owner=ctypes.c_ulong();ctypes.windll.user32.GetWindowThreadProcessId(hwnd,ctypes.byref(owner))
        if owner.value==pid:ctypes.windll.user32.ShowWindow(hwnd,4 if show else 0)
        return True
    ctypes.windll.user32.EnumWindows(callback(visit),0)
try:
    worker=UsageWorker();sample=worker.query({'threadId':ID,'hostId':'local'},True)
    report['checks']['usageSource']=sample['usage']['total_tokens']==full['total_tokens'] and sample['context']['usedTokens']==94667 and sample['context']['maxTokens']==258400
    report['checks']['ttft']=sample['ttft']['latestMs']==650
    report['checks']['invalid']=not worker.query({'threadId':'../auth.json'},True)['available']
    report['checks']['remote']=not worker.query({'threadId':ID,'hostId':'remote'},True)['available']
    report['checks']['missing']=not worker.query({'threadId':OTHER,'hostId':'local'},True)['available']
    report['checks']['noInventedSpeed']=sample['generation']['latest'] is None and sample['generation']['samples']==0
    env=os.environ.copy()
    for key in ['ELECTRON_RUN_AS_NODE','OPENAI_API_KEY','CODEX_API_KEY']:env.pop(key,None)
    env['CODEX_ELECTRON_USER_DATA_PATH']=str(OUT/'app-profile')
    env['CODEX_HOME']=str(OUT/'app-codex-home');(OUT/'app-codex-home').mkdir(exist_ok=True)
    with (OUT/'stdout.log').open('wb') as out,(OUT/'stderr.log').open('wb') as err:
        p=subprocess.Popen([str(APP/'ChatGPT.exe'),'--user-data-dir='+str(BROWSER),'--remote-debugging-port=0','--remote-debugging-address=127.0.0.1','--disable-renderer-backgrounding','--disable-background-timer-throttling'],cwd=APP,env=env,stdout=out,stderr=err,creationflags=0x08000000)
    deadline=time.monotonic()+40;target=None
    while time.monotonic()<deadline and p.poll() is None:
        window_display(p.pid,False)
        file=BROWSER/'DevToolsActivePort'
        if file.exists():
            try:
                port=int(file.read_text().splitlines()[0]);targets=json.loads(opener.open('http://127.0.0.1:'+str(port)+'/json/list',timeout=3).read())
            except (OSError,ValueError,IndexError):
                time.sleep(.2);continue
            target=next((t for t in targets if t.get('type')=='page' and t.get('url','').startswith('app://-')),None)
            if target:break
        time.sleep(.2)
    if not target:raise RuntimeError('Official App renderer unavailable')
    ready=CDP(target['webSocketDebuggerUrl'])
    for attempt in range(30):
        if ready.evaluate('location.protocol==="app:"&&!!document.getElementById("root")'):break
        time.sleep(.2)
    ready.close()
    adapter=TargetAdapter(target,worker);cdp=adapter.cdp
    fixture_script="""(()=>{
      document.getElementById('root').style.display='none';const fixture=document.createElement('main');fixture.id='stats-qa';fixture.style.cssText='position:absolute;left:20px;top:80px';document.body.append(fixture);
      window.qaSubmitted=false;
      window.qaSet=(width,layout,question)=>{
        const main=document.getElementById('stats-qa');main.style.width=width+'px';
        main.innerHTML=(question?'<section data-codex-composer-request-navigation style="height:130px;padding:12px;border:1px solid #888;border-radius:20px;box-sizing:border-box"><p>请观察显示是否稳定</p><button onclick="window.qaSubmitted=true">显示稳定</button></section>':'')+
        '<div data-codex-composer-root><div data-composer-surface-variant="default" data-composer-radius-variant="default" style="display:flex;flex-direction:column;border:1px solid #666;border-radius:24px;padding:8px;box-sizing:border-box"><div contenteditable style="min-height:28px">随心输入…</div><div data-composer-footer-responsive data-composer-layout="'+layout+'" style="display:flex;align-items:center;justify-content:space-between;gap:8px"><div><button data-composer-navigation-target="permissions">完全访问</button></div><div style="display:flex;gap:8px"><button data-composer-navigation-target="reasoning">GPT-6 Astra 极高⌄</button><button aria-label="停止" style="background:#4469c2;border-radius:50%;width:32px;height:32px;color:white">■</button></div></div></div></div>';
        const root=main.querySelector('[data-codex-composer-root]');root.__reactFiber$qa={memoizedProps:{isResponseInProgress:false},updateQueue:{memoCache:{data:[[{value:{kind:'local',clientThreadId:'local:11111111-1111-4111-8111-111111111111'}}]]}},return:null};
      };window.qaSet(620,'multiline',false);return true;
    })()"""
    cdp.evaluate(fixture_script)
    window_display(p.pid,True);time.sleep(1.8);cdp.evaluate('document.fonts.ready.then(()=>true)')
    report['checks']['binding']=cdp.evaluate("document.querySelector('#stats-qa .codex-native-stats').innerText.includes('53.6M tokens')")
    report['identityFormats']=[]
    for name,value in [('pure-uuid',{'kind':'local','clientThreadId':ID}),('typed-local',{'kind':'local','clientThreadId':'local:'+ID}),('native-conversation',{'kind':'local','clientThreadId':'local:'+ID,'conversationId':ID,'routeConversationId':ID})]:
        cdp.evaluate("document.querySelector('#stats-qa [data-codex-composer-root]').__reactFiber$qa.updateQueue.memoCache.data[0][0].value="+json.dumps(value)+";true");time.sleep(1.4)
        result=cdp.evaluate("(()=>{const r=document.querySelector('#stats-qa [data-codex-composer-root]'),b=r.querySelector('.codex-native-stats');return{thread:r.dataset.nativeStatsThread,visible:!b.hidden,numbers:b.innerText.includes('53.6M tokens')};})()")
        result.update(name=name,passed=result['thread']==ID and result['visible'] and result['numbers']);report['identityFormats'].append(result)
    report['checks']['identityFormats']=all(s['passed'] for s in report['identityFormats'])
    for width in [360,440,620,860]:
        for layout in ['multiline','single-line']:
            for question in [False,True,False]:
                cdp.evaluate('window.qaSet('+json.dumps(width)+','+json.dumps(layout)+','+json.dumps(question)+');true');time.sleep(1.5)
                deadline=time.monotonic()+8
                while time.monotonic()<deadline:
                    if cdp.evaluate("!!document.querySelector('#stats-qa .codex-native-stats:not([hidden])')"):break
                    time.sleep(.1)
                samples=[]
                for tick in range(30):
                    samples.append(cdp.evaluate("(()=>{const b=document.querySelector('#stats-qa .codex-native-stats'),s=document.querySelector('#stats-qa [data-composer-surface-variant]'),r=b.getBoundingClientRect();return[r.y,r.height,s.getBoundingClientRect().height].map(v=>Math.round(v*10)/10).concat(b.hidden,document.querySelector('.nst-panel').id);})()"));time.sleep(.05)
                state=cdp.evaluate("(()=>{const b=document.querySelector('#stats-qa .codex-native-stats'),r=b.getBoundingClientRect();return{oneInstance:document.querySelectorAll('#stats-qa .codex-native-stats').length===1,visible:!b.hidden,numbers:b.innerText.includes('tokens')&&b.innerText.includes('轮'),placement:b.dataset.placement,contained:[...b.querySelectorAll('.nst-trigger-label')].every(n=>{const q=n.getBoundingClientRect();return q.left>=r.left-1&&q.right<=r.right+1;})};})()")
                distinct=list({json.dumps(s) for s in samples});state.update(stable=len(distinct)==1,samples=[json.loads(s) for s in distinct])
                state.update(width=width,layout=layout,question=question);state['passed']=all(state[k] for k in ['stable','oneInstance','visible','numbers','contained']) and state['placement']=='footer';report['cases'].append(state)
                (OUT/'progress.json').write_text(json.dumps({'completed':len(report['cases']),'last':state}),encoding='utf-8')
    report['checks']['hover']=cdp.evaluate("document.querySelector('#stats-qa [data-view=usage]').dispatchEvent(new Event('pointerenter'));document.querySelector('.nst-panel').matches(':popover-open')")
    report['checks']['context']=cdp.evaluate("document.querySelector('.nst-context').innerText.includes('94,667 tok')&&document.querySelector('.nst-context').innerText.includes('258,400 tok')")
    report['toggle']=[]
    for on in [False,True,False,True]:
        switch(on);time.sleep(1.7)
        state=cdp.evaluate("(()=>{const b=document.querySelector('#stats-qa .codex-native-stats');return{visible:!b.hidden,popover:document.querySelector('.nst-panel').matches(':popover-open'),oneInstance:document.querySelectorAll('#stats-qa .codex-native-stats').length===1};})()")
        state.update(enabled=on,passed=state['visible']==on and state['oneInstance'] and (on or not state['popover']));report['toggle'].append(state)
    report['checks']['toggle']=all(s['passed'] for s in report['toggle'])
    cdp.evaluate("const root=document.querySelector('#stats-qa [data-codex-composer-root]');root.__reactFiber$qa.updateQueue.memoCache.data[0][0].value={kind:'new',browserTabMentionConversationId:null};true")
    time.sleep(1.4);report['checks']['newChatHidden']=cdp.evaluate("document.querySelector('#stats-qa .codex-native-stats').hidden")
    cdp.evaluate("document.querySelector('#stats-qa [data-codex-composer-root]').__reactFiber$qa.updateQueue.memoCache.data[0][0].value={kind:'local',clientThreadId:'local:11111111-1111-4111-8111-111111111111'};true")
    time.sleep(1.4);report['checks']['restore']=cdp.evaluate("!document.querySelector('#stats-qa .codex-native-stats').hidden&&document.querySelectorAll('#stats-qa .codex-native-stats').length===1")
    start_ms=cdp.evaluate("(()=>{const startedAtMs=Date.now();window.dispatchEvent(new MessageEvent('message',{data:{type:'mcp-notification',hostId:'local',method:'item/started',params:{threadId:'11111111-1111-4111-8111-111111111111',turnId:'two',item:{id:'speed-qa',type:'agentMessage'},startedAtMs}}}));return startedAtMs;})()")
    time.sleep(.6)
    end_ms=cdp.evaluate('Date.now()')
    updated={**full,'output_tokens':full['output_tokens']+100,'total_tokens':full['total_tokens']+100}
    speed_events=[{'type':'event_msg','timestamp':time.strftime('%Y-%m-%dT%H:%M:%S',time.gmtime(start_ms/1000))+'.'+str(start_ms%1000).zfill(3)+'Z','payload':{'type':'task_started','turn_id':'two'}},
                  {'type':'event_msg','timestamp':time.strftime('%Y-%m-%dT%H:%M:%S',time.gmtime(end_ms/1000))+'.'+str(end_ms%1000).zfill(3)+'Z','payload':{'type':'item_completed','turn_id':'two','item':{'id':'speed-qa','type':'AgentMessage'},'started_at_ms':start_ms,'completed_at_ms':end_ms}},
                  {'type':'token_usage_record','timestamp':time.strftime('%Y-%m-%dT%H:%M:%S',time.gmtime(end_ms/1000))+'.'+str(end_ms%1000).zfill(3)+'Z','payload':{'response_id':'speed-response','turn_id':'two','usage':{'output_tokens':100},'thread_token_usage':updated}}]
    with rollout.open('a',encoding='utf-8') as stream:stream.write(''.join(json.dumps(e)+'\n' for e in speed_events))
    cdp.evaluate("window.dispatchEvent(new MessageEvent('message',{data:{type:'mcp-notification',hostId:'local',method:'item/completed',params:{threadId:'11111111-1111-4111-8111-111111111111',turnId:'two',item:{id:'speed-qa',type:'agentMessage'},completedAtMs:"+str(end_ms)+"}}}));window.dispatchEvent(new MessageEvent('message',{data:{type:'mcp-notification',hostId:'local',method:'thread/tokenUsage/updated',params:{threadId:'11111111-1111-4111-8111-111111111111',turnId:'two',tokenUsage:{last:{outputTokens:100},total:{outputTokens:"+str(updated['output_tokens'])+"}}}}}));true")
    time.sleep(1.5)
    generation=cdp.evaluate("window.codexNativeStats.getStats({threadId:'11111111-1111-4111-8111-111111111111',hostId:'local'}).then(r=>r.generation)")
    report['speed']=generation
    report['checks']['completedReplySpeed']=generation['samples']==1 and abs(generation['latest']-100000/(end_ms-start_ms))<.001 and cdp.evaluate("document.querySelector('#stats-qa .nst-speed').innerText.includes('≈')")
    adapter.close();adapter=None
    adapter=TargetAdapter(target,worker);cdp=adapter.cdp;time.sleep(1.8)
    report['checks']['controllerReconnect']=cdp.evaluate("!document.querySelector('#stats-qa .codex-native-stats').hidden&&document.querySelector('#stats-qa .codex-native-stats').innerText.includes('53.6M tokens')&&document.querySelectorAll('#stats-qa .codex-native-stats').length===1")
    report['checks']['reconnectedBinding']=cdp.evaluate("window.codexNativeStats.getStats({threadId:'11111111-1111-4111-8111-111111111111',hostId:'local'}).then(r=>r.enabled===true&&r.usage?.total_tokens===53561883&&r.generation?.samples===1)")
    cdp.send('Page.reload');time.sleep(2)
    for attempt in range(30):
        if cdp.evaluate('location.protocol==="app:"&&!!document.getElementById("root")&&window.__codexStatsOfficialBridge===true'):break
        time.sleep(.2)
    cdp.evaluate(fixture_script);time.sleep(1.8)
    report['checks']['reloadWithTypedId']=cdp.evaluate("(()=>{const r=document.querySelector('#stats-qa [data-codex-composer-root]'),b=r?.querySelector('.codex-native-stats');return!!b&&!b.hidden&&r.dataset.nativeStatsThread==='11111111-1111-4111-8111-111111111111'&&b.innerText.includes('53.6M tokens');})()")
    report['checks']['speedAfterReload']=cdp.evaluate("document.querySelector('#stats-qa .nst-speed').innerText.includes('≈')")
    report['passed']=all(report['checks'].values()) and all(c['passed'] for c in report['cases'])
    import base64
    (OUT/'official-stats.png').write_bytes(base64.b64decode(cdp.send('Page.captureScreenshot',{'format':'png'})['data']))
except Exception as e:report.update(passed=False,error=type(e).__name__+': '+str(e))
finally:
    if adapter:
        try:adapter.cdp.send('Browser.close',wait=False)
        except Exception:pass
        adapter.close()
    if p:
        try:p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            import psutil
            process=psutil.Process(p.pid);assert '--user-data-dir='+str(BROWSER) in process.cmdline()
            for child in process.children(recursive=True):
                try:child.terminate()
                except psutil.Error:pass
            process.terminate()
    if worker:worker.close()
    (OUT/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'passed':report.get('passed'),'error':report.get('error'),'checks':report.get('checks'),'cases':len(report['cases'])},indent=2))
