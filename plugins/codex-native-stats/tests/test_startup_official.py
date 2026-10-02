"""Exercise startup recovery against the real official executable, isolated."""
import ctypes,json,os,subprocess,sys,time
from pathlib import Path
from unittest.mock import patch
import psutil

PLUGIN=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('CODEX_STATS_TEST_OUT',str(Path.home()/'CodexStatsValidation/release-startup')))
OUT.mkdir(parents=True,exist_ok=True)
os.environ['CODEX_HOME']=str(OUT/'codex-home')
os.environ['CODEX_STATS_PLUGIN_STATE']=str(OUT/'state')
home=Path(os.environ['CODEX_HOME']);home.mkdir(exist_ok=True)
(home/'config.toml').write_text('[plugins."codex-native-stats@codex-stats"]\nenabled=true\n',encoding='utf-8')
sys.path.insert(0,str(PLUGIN/'runtime'))
import official_adapter as adapter

app=adapter.installed_app();browser=OUT/'browser';adapter.BROWSER=browser
report={'officialExecutable':str(app),'isolatedProfile':str(browser),'checks':{}}
process=None

def hide_test_window():
    callback=ctypes.WINFUNCTYPE(ctypes.c_bool,ctypes.c_void_p,ctypes.c_void_p)
    def visit(hwnd,_):
        owner=ctypes.c_ulong();ctypes.windll.user32.GetWindowThreadProcessId(hwnd,ctypes.byref(owner))
        if process and owner.value==process.pid:ctypes.windll.user32.ShowWindow(hwnd,0)
        return True
    ctypes.windll.user32.EnumWindows(callback(visit),0)

try:
    env=os.environ.copy()
    for key in ['ELECTRON_RUN_AS_NODE','OPENAI_API_KEY','CODEX_API_KEY']:env.pop(key,None)
    env['CODEX_ELECTRON_USER_DATA_PATH']=str(OUT/'app-profile')
    report['checks']['noOldEndpoint']=adapter.debug_port() is None
    with (OUT/'stdout.log').open('wb') as out,(OUT/'stderr.log').open('wb') as err:
        process=subprocess.Popen([str(app),'--user-data-dir='+str(browser),'--remote-debugging-port=0','--remote-debugging-address=127.0.0.1'],cwd=app.parent,env=env,stdout=out,stderr=err,creationflags=0x08000000)
    deadline=time.monotonic()+30
    def own_pids():
        hide_test_window()
        return [process.pid] if process.poll() is None and time.monotonic()<deadline else []
    started=time.monotonic()
    # Reproduce the observed disagreement: original check stays unavailable,
    # while a fresh process can validate the live official endpoint.
    with patch.object(adapter,'official_pids',side_effect=own_pids),patch.object(adapter,'debug_port',return_value=None),patch.object(adapter,'start_official') as restart:
        port=adapter.wait_for_renderer()
        report['checks']['noRestart']=restart.call_count==0
    report['recoverySeconds']=round(time.monotonic()-started,3)
    report['checks']['freshRecovery']=port is not None and json.loads((adapter.STATE/'status.json').read_text())['recoveredByFreshProbe']
    report['checks']['originalValidation']=adapter.debug_port(browser)==port and port is not None
    report['checks']['freshValidation']=adapter.fresh_debug_port(browser)==port and port is not None
    wrong=OUT/'wrong-profile';wrong.mkdir(exist_ok=True)
    (wrong/'DevToolsActivePort').write_text(str(port)+'\n',encoding='utf-8')
    report['checks']['rejectWrongProfile']=adapter.fresh_debug_port(wrong) is None
    targets=adapter.endpoint_targets(port)
    report['checks']['officialRenderer']=any(t.get('url','').startswith('app://-') for t in targets)
    report['passed']=all(report['checks'].values())
except Exception as error:report.update(passed=False,error=str(error))
finally:
    if process and process.poll() is None:
        owned=psutil.Process(process.pid)
        assert '--user-data-dir='+str(browser) in owned.cmdline()
        for child in owned.children(recursive=True):
            try:child.terminate()
            except psutil.Error:pass
        owned.terminate()
    (OUT/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)
sys.exit(0 if report['passed'] else 1)
