"""Load statistics inside the installed official App through its renderer endpoint."""
from pathlib import Path
import argparse,ctypes,hashlib,json,os,queue,secrets,shutil,subprocess,sys,threading,time,tomllib,urllib.request
import psutil,websocket

ROOT=Path(__file__).resolve().parent
PLUGIN_ID=os.environ.get('CODEX_STATS_PLUGIN_ID','codex-native-stats@codex-stats')
HOME=Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex')))
STATE=Path(os.environ.get('CODEX_STATS_PLUGIN_STATE',str(HOME/'plugins/state/codex-native-stats')))
APP_PROFILE=Path.home()/'AppData/Roaming/Codex'
BROWSER=APP_PROFILE/'web/Codex'
APP_ID='OpenAI.Codex_2p2nqsd0c76g0!App'
NODE=os.environ.get('CODEX_STATS_NODE') or shutil.which('node')
_settings_key=None;_enabled=False;_endpoint_diagnostic={'reason':'not-checked'}

def enabled():
    global _settings_key,_enabled
    try:
        p=HOME/'config.toml';s=p.stat();key=(s.st_mtime_ns,s.st_size)
        if key!=_settings_key:
            data=tomllib.loads(p.read_text(encoding='utf-8-sig'))
            _enabled=data.get('plugins',{}).get(PLUGIN_ID,{}).get('enabled') is True;_settings_key=key
        return _enabled
    except Exception:return False

def registered():
    try:return PLUGIN_ID in tomllib.loads((HOME/'config.toml').read_text(encoding='utf-8-sig')).get('plugins',{})
    except Exception:return False

def status(state,**details):
    STATE.mkdir(parents=True,exist_ok=True)
    value={'state':state,'pid':os.getpid(),'updatedAt':time.time(),**details}
    temp=STATE/('status-'+str(os.getpid())+'.next.json');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(temp,STATE/'status.json')

def installed_app():
    script="[Console]::OutputEncoding=[Text.Encoding]::UTF8; (Get-AppxPackage -Name OpenAI.Codex | Sort-Object Version -Descending | Select-Object -First 1).InstallLocation"
    result=subprocess.run(['powershell.exe','-NoProfile','-Command',script],capture_output=True,encoding='utf-8',timeout=15,creationflags=0x08000000,check=True)
    root=Path(result.stdout.strip());exe=root/'app/ChatGPT.exe'
    if root.parent.name.lower()!='windowsapps' or not root.name.lower().startswith('openai.codex_') or not exe.is_file():raise RuntimeError('Official Store App executable not found')
    return exe

def official_pids():
    found=[]
    for process in psutil.process_iter(['name','exe']):
        try:
            if (process.info['name'] or '').lower()!='chatgpt.exe':continue
            if 'windowsapps\\openai.codex_' in (process.info['exe'] or '').lower():found.append(process.pid)
        except psutil.Error:pass
    return found

def official_debug_requested():
    for process in psutil.process_iter(['name','exe','cmdline']):
        try:
            info=process.info;args=info['cmdline'] or []
            if (info['name'] or '').lower()!='chatgpt.exe' or 'windowsapps\\openai.codex_' not in (info['exe'] or '').lower():continue
            if any(a.startswith('--type=') for a in args):continue
            if '--user-data-dir='+str(BROWSER) in args and any(a.startswith('--remote-debugging-port=') for a in args):return True
        except psutil.Error:pass
    return False

def wait_for_renderer():
    status('waiting_for_renderer',enabled=enabled(),willNotTerminateApp=True)
    previous=None;last_fresh_check=time.monotonic()
    while official_pids():
        if not registered():status('cancelled',reason='plugin-uninstalled');return None
        if (STATE/'cancel.signal').exists():status('cancelled');return None
        port=debug_port()
        if port:return port
        if time.monotonic()-last_fresh_check>=5:
            last_fresh_check=time.monotonic()
            port=fresh_debug_port()
            if port:
                status('renderer_ready',recoveredByFreshProbe=True,port=port)
                return port
        if previous!=_endpoint_diagnostic:
            previous=dict(_endpoint_diagnostic)
            status('waiting_for_renderer',enabled=enabled(),willNotTerminateApp=True,endpoint=previous)
        time.sleep(.5)
    status('stopped',reason='official-app-closed-before-renderer-ready')
    return None

def fresh_debug_port(browser=None):
    """Recheck stalled startup outside the process that activated the package."""
    global _endpoint_diagnostic
    browser=BROWSER if browser is None else browser
    python=str(Path(sys.executable).with_name('python.exe'))
    try:
        result=subprocess.run([python,str(ROOT/'endpoint_probe.py'),str(browser)],capture_output=True,encoding='utf-8',timeout=5,creationflags=0x08000000,check=True)
        data=json.loads(result.stdout);port=data.get('port')
        _endpoint_diagnostic=data.get('diagnostic',{'reason':'fresh-probe-unavailable'})
        if isinstance(port,int) and not isinstance(port,bool) and 1<=port<=65535 and _endpoint_diagnostic.get('reason')=='ready':return port
    except (OSError,ValueError,subprocess.SubprocessError):
        _endpoint_diagnostic={'reason':'fresh-probe-unavailable'}
    return None

def controller_running(pid):
    try:
        process=psutil.Process(pid)
        return process.is_running() and process.name().lower() in ['python.exe','pythonw.exe'] and any(Path(a).resolve()==ROOT/'official_adapter.py' for a in process.cmdline()[1:] if a.endswith('.py'))
    except (TypeError,ValueError,psutil.Error):return False

def focus_official():
    pids=set(official_pids());callback=ctypes.WINFUNCTYPE(ctypes.c_bool,ctypes.c_void_p,ctypes.c_void_p)
    def visit(hwnd,_):
        owner=ctypes.c_ulong();ctypes.windll.user32.GetWindowThreadProcessId(hwnd,ctypes.byref(owner))
        if owner.value in pids and ctypes.windll.user32.IsWindowVisible(hwnd):
            ctypes.windll.user32.ShowWindow(hwnd,9);ctypes.windll.user32.SetForegroundWindow(hwnd);return False
        return True
    ctypes.windll.user32.EnumWindows(callback(visit),0)

def endpoint_port_files(browser):
    """MSIX and desktop processes see different views of the Roaming path."""
    files=[browser/'DevToolsActivePort']
    roaming=Path.home()/'AppData/Roaming'
    try:
        relative=browser.relative_to(roaming)
        package=Path.home()/'AppData/Local/Packages'/APP_ID.split('!')[0]
        files.append(package/'LocalCache/Roaming'/relative/'DevToolsActivePort')
    except ValueError:pass
    return files

def debug_port(browser=None):
    global _endpoint_diagnostic
    browser=BROWSER if browser is None else Path(browser)
    files=endpoint_port_files(browser)
    _endpoint_diagnostic={'reason':'port-file-unavailable','profile':str(browser),'checkedFiles':[str(p) for p in files]}
    connections=None
    for file in files:
        try:
            port=int(file.read_text().splitlines()[0])
            _endpoint_diagnostic.update(port=port,portFile=str(file))
            if not 1<=port<=65535:_endpoint_diagnostic['reason']='invalid-port';continue
            if connections is None:connections=psutil.net_connections(kind='tcp')
            listeners=[c for c in connections if c.status=='LISTEN' and c.laddr.port==port]
            if not listeners:_endpoint_diagnostic['reason']='listener-not-ready';continue
            if any(c.laddr.ip not in ['127.0.0.1','::1'] for c in listeners):_endpoint_diagnostic['reason']='non-loopback-listener';continue
            for connection in listeners:
                try:
                    process=psutil.Process(connection.pid)
                    if 'windowsapps\\openai.codex_' not in process.exe().lower():_endpoint_diagnostic['reason']='unexpected-listener-owner';continue
                    args=process.cmdline()
                    profiles=[arg.split('=',1)[1] for arg in args if arg.startswith('--user-data-dir=')]
                    if any(os.path.normcase(os.path.normpath(profile))==os.path.normcase(os.path.normpath(browser)) for profile in profiles):
                        _endpoint_diagnostic={'reason':'ready','port':port,'ownerPid':process.pid,'portFile':str(file)};return port
                    _endpoint_diagnostic['reason']='listener-profile-mismatch'
                except psutil.Error as e:_endpoint_diagnostic.update(reason='listener-inspection-error',error=type(e).__name__)
        except FileNotFoundError:continue
        except (OSError,ValueError,IndexError,psutil.Error) as e:_endpoint_diagnostic.update(reason='endpoint-check-error',error=type(e).__name__)
    return None

def start_official():
    if official_pids():raise RuntimeError('Wait for the current official App to exit normally')
    exe=installed_app();pid=activate_package(subprocess.list2cmdline(['--user-data-dir='+str(BROWSER),'--remote-debugging-port=0','--remote-debugging-address=127.0.0.1']))
    status('starting',officialExecutable=str(exe),appPid=pid,browserProfile=str(BROWSER))
    return psutil.Process(pid)

def activation_manager():
    import uuid
    class GUID(ctypes.Structure):
        _fields_=[('Data1',ctypes.c_uint32),('Data2',ctypes.c_uint16),('Data3',ctypes.c_uint16),('Data4',ctypes.c_ubyte*8)]
        @classmethod
        def parse(cls,value):return cls.from_buffer_copy(uuid.UUID(value).bytes_le)
    ole=ctypes.OleDLL('ole32');initialized=ole.CoInitializeEx(None,2) in (0,1)
    clsid=GUID.parse('45BA127D-10A8-46EA-8AB7-56EA9078943C');iid=GUID.parse('2e941141-7f97-4756-ba1d-9decde894a3d');pointer=ctypes.c_void_p()
    ole.CoCreateInstance.argtypes=[ctypes.POINTER(GUID),ctypes.c_void_p,ctypes.c_uint32,ctypes.POINTER(GUID),ctypes.POINTER(ctypes.c_void_p)]
    result=ole.CoCreateInstance(ctypes.byref(clsid),None,1,ctypes.byref(iid),ctypes.byref(pointer))
    if result<0:raise OSError('Official package activation manager is unavailable: '+hex(result & 0xffffffff))
    table=ctypes.cast(pointer,ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    release=ctypes.WINFUNCTYPE(ctypes.c_ulong,ctypes.c_void_p)(table[2])
    def close():
        release(pointer)
        if initialized:ole.CoUninitialize()
    return pointer,table,close

def activate_package(arguments):
    pointer,table,close=activation_manager()
    try:
        activate=ctypes.WINFUNCTYPE(ctypes.c_long,ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_uint32,ctypes.POINTER(ctypes.c_uint32))(table[3]);pid=ctypes.c_uint32()
        result=activate(pointer,APP_ID,arguments,2,ctypes.byref(pid))
        if result<0:raise OSError('Official App activation failed: '+hex(result & 0xffffffff))
        return pid.value
    finally:close()

class UsageWorker:
    def __init__(self):
        if not NODE:raise RuntimeError('Bundled Node runtime is missing; repair the Windows package')
        self.lock=threading.Lock();self.pending={};self.serial=0
        STATE.mkdir(parents=True,exist_ok=True)
        self.log=(STATE/'usage-worker.log').open('ab')
        self.process=subprocess.Popen([NODE,'--disable-warning=ExperimentalWarning',str(ROOT/'usage-worker.cjs')],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,encoding='utf-8',bufsize=1,creationflags=0x08000000)
        threading.Thread(target=self.receive,daemon=True).start()
    def receive(self):
        for line in self.process.stdout:
            try:
                data=json.loads(line);waiter=self.pending.get(data.get('id'))
                if waiter:waiter.put(data.get('result'))
            except Exception:pass
    def query(self,request,plugin_enabled=None):
        with self.lock:
            self.serial+=1;ident=self.serial;waiter=queue.Queue(1);self.pending[ident]=waiter
            self.process.stdin.write(json.dumps({'id':ident,'request':request,'enabled':enabled() if plugin_enabled is None else plugin_enabled})+'\n');self.process.stdin.flush()
        try:return waiter.get(timeout=9)
        except queue.Empty:return {'available':False,'enabled':True,'reason':'statistics-timeout'}
        finally:self.pending.pop(ident,None)
    def close(self):
        try:self.process.stdin.close();self.process.wait(timeout=3)
        except Exception:self.process.terminate()
        self.log.close()

class CDP:
    def __init__(self,url):
        self.ws=websocket.create_connection(url,timeout=1,suppress_origin=True,http_no_proxy=['127.0.0.1','localhost','::1'])
        self.lock=threading.Lock();self.pending={};self.serial=0;self.events=queue.Queue();self.alive=True;self.contexts={}
        threading.Thread(target=self.receive,daemon=True).start()
    def receive(self):
        while self.alive:
            try:
                raw=self.ws.recv()
                if not raw:break
                message=json.loads(raw)
                if 'id' in message:
                    waiter=self.pending.get(message['id'])
                    if waiter:waiter.put(message)
                else:
                    if message.get('method')=='Runtime.executionContextCreated':
                        ctx=message['params']['context'];self.contexts[ctx['id']]=ctx.get('auxData',{})
                    elif message.get('method')=='Runtime.executionContextsCleared':self.contexts.clear()
                    if message.get('method') in ['Runtime.bindingCalled','Page.frameNavigated']:self.events.put(message)
            except websocket.WebSocketTimeoutException:continue
            except Exception:break
        self.alive=False
    def send(self,method,params=None,wait=True,timeout=10):
        with self.lock:
            self.serial+=1;ident=self.serial;waiter=queue.Queue(1)
            if wait:self.pending[ident]=waiter
            self.ws.send(json.dumps({'id':ident,'method':method,'params':params or {}}))
        if not wait:return
        try:
            message=waiter.get(timeout=timeout)
            if 'error' in message:raise RuntimeError(message['error'])
            return message.get('result',{})
        finally:self.pending.pop(ident,None)
    def evaluate(self,expression,timeout=10):
        result=self.send('Runtime.evaluate',{'expression':expression,'awaitPromise':True,'returnByValue':True},timeout=timeout)
        if result.get('exceptionDetails'):
            details=result['exceptionDetails'];raise RuntimeError(details.get('exception',{}).get('description') or details.get('text','Renderer expression failed'))
        return result.get('result',{}).get('value')
    def close(self):
        self.alive=False
        try:self.ws.close()
        except Exception:pass

def injection(token):
    sampler=(ROOT/'speed-stream.js').read_text(encoding='utf-8')
    bridge=(ROOT/'official-bridge.js').read_text(encoding='utf-8').replace('__STATS_BINDING_TOKEN__',json.dumps(token))
    renderer=(ROOT/'native-stats-renderer.js').read_text(encoding='utf-8')
    return '(()=>{if(location.protocol!=="app:"||location.hostname!=="-"||window.top!==window)return;const install=()=>{'+sampler+'\n'+bridge+'\n'+renderer+'};if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",install,{once:true});else install();})();'

class TargetAdapter:
    def __init__(self,target,worker):
        self.cdp=CDP(target['webSocketDebuggerUrl']);self.worker=worker;self.token=secrets.token_hex(24)
        self.main_frame=self.cdp.send('Page.getFrameTree')['frameTree']['frame']['id']
        self.cdp.send('Runtime.enable');self.cdp.send('Page.enable');self.cdp.send('Runtime.addBinding',{'name':'__codexStatsBinding'})
        script=injection(self.token)
        self.cdp.send('Page.addScriptToEvaluateOnNewDocument',{'source':script});self.cdp.evaluate(script)
        threading.Thread(target=self.handle,daemon=True).start()
    def handle(self):
        while self.cdp.alive:
            try:event=self.cdp.events.get(timeout=.5)
            except queue.Empty:continue
            if event.get('method')=='Page.frameNavigated' and not event.get('params',{}).get('frame',{}).get('parentId'):
                self.main_frame=event['params']['frame']['id']
            if event.get('method')!='Runtime.bindingCalled':continue
            params=event.get('params',{});context=params.get('executionContextId');aux=self.cdp.contexts.get(context,{})
            if params.get('name')!='__codexStatsBinding' or aux.get('frameId')!=self.main_frame or not aux.get('isDefault'):continue
            try:
                payload=params['payload']
                if len(payload)>16384:continue
                data=json.loads(payload);ident=data.get('id')
                if data.get('token')!=self.token or not isinstance(ident,int) or not 0<ident<2**53:continue
                result=self.worker.query(data.get('request'))
                expression='window.__codexStatsResolve?.('+str(ident)+','+json.dumps(result,ensure_ascii=True)+')'
                self.cdp.send('Runtime.evaluate',{'expression':expression,'contextId':context},wait=False)
            except Exception:continue
    def close(self):self.cdp.close()

def endpoint_targets(port):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    targets=json.loads(opener.open('http://127.0.0.1:'+str(port)+'/json/list',timeout=3).read())
    return [t for t in targets if t.get('type')=='page' and t.get('url','').startswith('app://-')]

def inspect_ui():
    port=debug_port()
    if not port:return {'checked':False,'reason':'no-valid-renderer-endpoint','visibleControls':0}
    expression="""(()=>({installed:window.__codexNativeStatsInstalled===true,bridge:window.__codexStatsOfficialBridge===true,composers:[...document.querySelectorAll('[data-codex-composer-root]')].map(root=>{const bar=root.querySelector('.codex-native-stats'),r=root.getBoundingClientRect(),b=bar?.getBoundingClientRect(),s=bar?.closest('[data-composer-surface-variant]')?.getBoundingClientRect();return{active:r.width>0&&r.height>0,threadId:root.dataset.nativeStatsThread||null,identityKind:root.dataset.nativeStatsIdentityKind||'unknown',hasControl:!!bar,visible:!!b&&!bar.hidden&&b.width>0&&b.height>0,placement:bar?.dataset.placement,insideInputBar:!!b&&!!s&&b.left>=s.left&&b.right<=s.right&&b.top>=s.top&&b.bottom<=s.bottom};})}))()"""
    pages=[]
    for target in endpoint_targets(port):
        connection=None
        try:
            connection=CDP(target['webSocketDebuggerUrl']);pages.append(connection.evaluate(expression,timeout=2))
        except Exception:pages.append({'error':'renderer-inspection-unavailable','composers':[]})
        finally:
            if connection:connection.close()
    composers=[c for p in pages for c in p.get('composers',[]) if c['active']]
    return {'checked':any('error' not in p for p in pages),'scriptInstalled':any(p.get('installed') for p in pages),'activeComposers':len(composers),'visibleControls':sum(c['visible'] for c in composers),'missingControls':sum(not c['visible'] and c['identityKind']!='new' for c in composers) if enabled() else 0,'composers':composers}

def run(wait_for_exit=False,focus=False):
    STATE.mkdir(parents=True,exist_ok=True)
    kernel=ctypes.windll.kernel32;kernel.CreateMutexW.restype=ctypes.c_void_p
    state_key=hashlib.sha256(str(STATE.resolve()).casefold().encode()).hexdigest()[:24]
    mutex=kernel.CreateMutexW(None,True,'Local\\CodexOfficialStatsPlugin-'+state_key)
    if kernel.GetLastError()==183:
        kernel.CloseHandle(ctypes.c_void_p(mutex))
        if focus:focus_official()
        return
    adapters={};worker=None
    try:
        port=debug_port()
        if official_pids() and not port:
            if focus:focus_official()
            if official_debug_requested():
                port=wait_for_renderer()
                if not port:return
            elif not wait_for_exit:
                status('requires_normal_restart');return
            else:
                status('waiting_for_exit',willNotTerminateApp=True)
                while official_pids():
                    if not registered():status('cancelled',reason='plugin-uninstalled');return
                    if (STATE/'cancel.signal').exists():status('cancelled');return
                    port=debug_port()
                    if port:break
                    time.sleep(.5)
        if not port:
            start_official();port=wait_for_renderer()
            if not port:return
        worker=UsageWorker();status('active',enabled=enabled(),officialExecutable=str(installed_app()),port=port,endpoint=dict(_endpoint_diagnostic))
        last_enabled=enabled();had_target=False;empty_since=None;uninstalled_since=None
        while True:
            if (STATE/'cancel.signal').exists():
                status('stopped',reason='cancel-requested');break
            if not registered():
                if uninstalled_since is None:
                    uninstalled_since=time.monotonic()
                elif time.monotonic()-uninstalled_since>2.5:status('stopped',reason='plugin-uninstalled');break
            else:uninstalled_since=None
            try:targets=endpoint_targets(port)
            except Exception:
                if not official_pids():break
                new_port=debug_port()
                if new_port and new_port!=port:
                    for current in adapters.values():current.close()
                    adapters.clear();port=new_port
                time.sleep(.5);continue
            active_ids={t['id'] for t in targets}
            for ident,adapter in list(adapters.items()):
                if ident not in active_ids or not adapter.cdp.alive:adapter.close();del adapters[ident]
            for target in targets:
                if target['id'] not in adapters:
                    try:adapters[target['id']]=TargetAdapter(target,worker);had_target=True
                    except Exception as e:status('adapter_retry',reason=type(e).__name__)
            now_enabled=enabled()
            if now_enabled!=last_enabled:
                status('active',enabled=now_enabled,port=port);last_enabled=now_enabled
            if targets:empty_since=None
            elif had_target:
                empty_since=empty_since or time.monotonic()
                if time.monotonic()-empty_since>5 and not official_pids():break
            time.sleep(.4)
        status('stopped',reason='official-app-closed')
    except Exception as e:status('failed',reason=str(e))
    finally:
        for adapter in adapters.values():adapter.close()
        if worker:worker.close()
        kernel.ReleaseMutex(ctypes.c_void_p(mutex));kernel.CloseHandle(ctypes.c_void_p(mutex))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--wait-for-exit',action='store_true');parser.add_argument('--focus',action='store_true');args=parser.parse_args()
    run(args.wait_for_exit,args.focus)
