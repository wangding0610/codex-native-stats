"""Check renderer access using the installed official executable and an empty profile."""
from pathlib import Path
import ctypes,json,os,subprocess,time,urllib.request,sys
import psutil,websocket
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
from official_adapter import debug_port

PLUGIN=Path(__file__).resolve().parents[1]
OUT=Path.home()/'AppData/Local/CodexStatsPlugin/validation/official-probe';OUT.mkdir(parents=True,exist_ok=True)
from official_adapter import installed_app
APP=installed_app().parent
BROWSER=OUT/'browser';HOME=OUT/'codex-home';HOME.mkdir(exist_ok=True)
report={'officialExecutable':str(APP/'ChatGPT.exe'),'isolatedProfile':str(BROWSER)}
env=os.environ.copy()
for key in ['ELECTRON_RUN_AS_NODE','OPENAI_API_KEY','CODEX_API_KEY','CODEX_NATIVE_STATS_QA','CODEX_NATIVE_STATS_SMOKE']:env.pop(key,None)
env.update(CODEX_HOME=str(HOME),CODEX_ELECTRON_USER_DATA_PATH=str(OUT/'app-profile'))
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
p=None;ws=None
def hide_window(pid):
    callback=ctypes.WINFUNCTYPE(ctypes.c_bool,ctypes.c_void_p,ctypes.c_void_p)
    def visit(hwnd,_):
        owner=ctypes.c_ulong();ctypes.windll.user32.GetWindowThreadProcessId(hwnd,ctypes.byref(owner))
        if owner.value==pid:ctypes.windll.user32.ShowWindow(hwnd,0)
        return True
    ctypes.windll.user32.EnumWindows(callback(visit),0)

try:
    with (OUT/'stdout.log').open('wb') as out,(OUT/'stderr.log').open('wb') as err:
        p=subprocess.Popen([str(APP/'ChatGPT.exe'),'--user-data-dir='+str(BROWSER),'--remote-debugging-port=0','--remote-debugging-address=127.0.0.1','--no-first-run'],cwd=APP,env=env,stdout=out,stderr=err,creationflags=0x08000000)
    report['pid']=p.pid;deadline=time.monotonic()+45;target=None
    while time.monotonic()<deadline and p.poll() is None:
        hide_window(p.pid)
        port_file=BROWSER/'DevToolsActivePort'
        if port_file.exists():
            port=int(port_file.read_text().splitlines()[0]);report['port']=port
            try:
                targets=json.loads(opener.open('http://127.0.0.1:'+str(port)+'/json/list',timeout=2).read())
                target=next((t for t in targets if t.get('type')=='page' and t.get('url','').startswith('app://-')),None)
                if target:break
            except Exception:pass
        time.sleep(.25)
    if not target:raise RuntimeError('Official renderer debug endpoint was not available; exit code '+str(p.poll()))
    ws=websocket.create_connection(target['webSocketDebuggerUrl'],timeout=5,suppress_origin=True)
    for attempt in range(20):
        ident=attempt+1
        ws.send(json.dumps({'id':ident,'method':'Runtime.evaluate','params':{'expression':'JSON.stringify({protocol:location.protocol,root:!!document.getElementById("root"),modelContext:typeof navigator.modelContext})','returnByValue':True}}))
        while True:
            result=json.loads(ws.recv())
            if result.get('id')==ident:break
        try:report['renderer']=json.loads(result['result']['result']['value'])
        except Exception:continue
        if report['renderer']['protocol']=='app:' and report['renderer']['root']:break
        time.sleep(.2)
    report['verifiedEndpoint']=debug_port(BROWSER)==port;report['passed']=report['renderer']['protocol']=='app:' and report['renderer']['root'] and report['verifiedEndpoint']
except Exception as e:report.update(passed=False,error=str(e))
finally:
    if ws:
        try:ws.send(json.dumps({'id':99,'method':'Browser.close'}));ws.close()
        except Exception:pass
    if p:
        try:p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process=psutil.Process(p.pid)
            assert '--user-data-dir='+str(BROWSER) in process.cmdline(),'Refusing to stop a different App instance'
            for child in process.children(recursive=True):
                try:child.terminate()
                except psutil.Error:pass
            process.terminate()
    (OUT/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
