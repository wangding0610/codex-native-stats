"""Small local MCP entry point for managing the official input-bar adapter."""
from pathlib import Path
import json,os,subprocess,sys
import psutil
sys.path.insert(0,str(Path(__file__).resolve().parent))
import official_adapter as adapter

VERSION='3.0.2'
def ensure_adapter(focus=False):
    adapter.STATE.mkdir(parents=True,exist_ok=True)
    (adapter.STATE/'cancel.signal').unlink(missing_ok=True)
    try:
        previous=json.loads((adapter.STATE/'status.json').read_text(encoding='utf-8'))
        if adapter.controller_running(previous.get('pid')):
            if focus:adapter.focus_official()
            return {'started':False,'alreadyRunning':True,'pid':previous['pid']}
    except (OSError,ValueError):pass
    pythonw=Path(sys.executable).with_name('pythonw.exe')
    runner=adapter.ROOT/'official_adapter.py'
    with (adapter.STATE/'adapter-process.log').open('ab') as log:
        options=dict(cwd=runner.parent,stdin=subprocess.DEVNULL,stdout=log,stderr=log)
        command=[str(pythonw),str(runner),'--wait-for-exit',*(['--focus'] if focus else [])]
        flags=0x08000000|0x00000200
        try:child=subprocess.Popen(command,creationflags=flags|0x01000000,**options)
        except OSError as e:
            if e.winerror!=5:raise
            child=subprocess.Popen(command,creationflags=flags,**options)
    return {'started':True,'pid':child.pid}

def get_status():
    file=adapter.STATE/'status.json'
    state=json.loads(file.read_text(encoding='utf-8')) if file.exists() else {'state':'not_started'}
    state['controllerRunning']=adapter.controller_running(state.get('pid'))
    if state.get('state') in ['active','starting','waiting_for_renderer','renderer_ready','waiting_for_exit','adapter_retry'] and not state['controllerRunning']:state['state']='disconnected'
    if state.get('state')=='waiting_for_exit':
        state['reason']='running-app-has-no-renderer-endpoint'
        state['action']='正常退出 App；统计后台会重新打开官方客户端。继续等待当前窗口加载不会启用控件。'
    try:ui=adapter.inspect_ui()
    except Exception:ui={'checked':False,'reason':'renderer-inspection-unavailable'}
    return {'pluginId':adapter.PLUGIN_ID,'version':VERSION,'enabled':adapter.enabled(),'adapter':state,'ui':ui,'officialClient':True}

TOOLS=[{'name':'statistics_status','description':'Check whether the official App input-bar statistics plugin is enabled and loaded.','inputSchema':{'type':'object','properties':{},'additionalProperties':False},'annotations':{'readOnlyHint':True,'destructiveHint':False,'openWorldHint':False}},
       {'name':'start_input_bar_statistics','description':'Start the local statistics adapter for the installed official App. If the App is running without its endpoint, wait for a normal exit; never terminate an active task.','inputSchema':{'type':'object','properties':{},'additionalProperties':False},'annotations':{'readOnlyHint':False,'destructiveHint':False,'openWorldHint':False}}]

def dispatch(method,params):
    if method=='initialize':return {'protocolVersion':params.get('protocolVersion','2024-11-05'),'capabilities':{'tools':{}},'serverInfo':{'name':'codex-input-bar-statistics','version':VERSION}}
    if method=='ping':return {}
    if method=='tools/list':return {'tools':TOOLS}
    if method=='tools/call':
        name=params.get('name')
        if name=='start_input_bar_statistics':result=ensure_adapter()
        elif name=='statistics_status':result=get_status()
        else:raise ValueError('Unknown statistics tool')
        return {'content':[{'type':'text','text':json.dumps(result,ensure_ascii=False)}],'structuredContent':result}
    raise ValueError('Unknown method')

def main():
    if adapter.enabled() and os.environ.get('CODEX_STATS_PLUGIN_NO_AUTOSTART')!='1':ensure_adapter()
    for line in sys.stdin:
        message=None
        try:
            message=json.loads(line)
            if 'id' not in message:continue
            result=dispatch(message.get('method'),message.get('params') or {})
            response={'jsonrpc':'2.0','id':message['id'],'result':result}
        except Exception as e:response={'jsonrpc':'2.0','id':message.get('id') if isinstance(message,dict) else None,'error':{'code':-32603,'message':str(e)}}
        print(json.dumps(response,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
