"""Exercise the actual setup/CLI/embedded host with an isolated install and home."""
from pathlib import Path
import hashlib, json, os, queue, shutil, subprocess, sys, threading, time, tomllib

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'validation'/('distribution-'+str(int(time.time())))
PAYLOAD = ROOT/'build/payload'
VERSION = (ROOT/'VERSION').read_text().strip()
HOME = OUT/'codex-home'
INSTALL = OUT/'安装 测试'
HOME.mkdir(parents=True)
report = {'checks':{},'productionTouched':False}

def digest(file):
    return hashlib.sha256(file.read_bytes()).hexdigest() if file.exists() else None

production_config = Path.home()/'.codex/config.toml'
production_before = digest(production_config)
synthetic = b'synthetic preservation sentinel\n'
(HOME/'auth.json').write_bytes(synthetic)
(HOME/'chat-sentinel.jsonl').write_bytes(synthetic)
(HOME/'config.toml').write_text('model = "sentinel-model"\n[model_providers.sentinel]\nname = "Sentinel"\nbase_url = "http://127.0.0.1:1234/v1"\n',encoding='utf-8')
env = os.environ.copy()
env.update(CODEX_HOME=str(HOME), CODEX_STATS_PLUGIN_NO_AUTOSTART='1',
           CODEX_STATS_INSTALL_ROOT=str(INSTALL), PYTHONIOENCODING='utf-8')
python = PAYLOAD/'python/python.exe'
installer = PAYLOAD/'installer/install.py'

def run(command, expected=0):
    result = subprocess.run(list(map(str,command)),env=env,capture_output=True,
                            encoding='utf-8',timeout=150,creationflags=0x08000000)
    if result.returncode!=expected:
        raise AssertionError(f'Unexpected exit {result.returncode}: '+result.stdout+result.stderr)
    return result

def check(name, condition):
    report['checks'][name]=bool(condition)
    if not condition: raise AssertionError(name)
    print('PASS '+name,flush=True)

def installed_version(): return (INSTALL/'current-version.txt').read_text().strip()

def config(): return tomllib.loads((HOME/'config.toml').read_text(encoding='utf-8'))

def hold_server():
    host = next((HOME/'plugins/cache').rglob('CodexStatsHost.exe'))
    process = subprocess.Popen([str(host)],cwd=host.parents[2],env=env,stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',creationflags=0x08000000)
    process.stdin.write('{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n')
    process.stdin.flush()
    reply=queue.Queue()
    threading.Thread(target=lambda: reply.put(process.stdout.readline()),daemon=True).start()
    try: line=reply.get(timeout=15)
    except queue.Empty:
        process.terminate();raise AssertionError('Interactive MCP handshake timed out')
    if 'result' not in json.loads(line): raise AssertionError('MCP failed to start')
    return process

def protocol():
    cache = list((HOME/'plugins/cache').rglob('CodexStatsHost.exe'))
    if len(cache)!=1: raise AssertionError('Expected exactly one installed plugin host: '+str(cache))
    # Match the manifest's cmd.exe /d /c relative path and actual cache cwd.
    process = subprocess.Popen(['cmd.exe','/d','/c',r'runtime\bin\CodexStatsHost.exe'],
        cwd=cache[0].parents[2],env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,text=True,encoding='utf-8',creationflags=0x08000000)
    messages = [
        {'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2024-11-05'}},
        {'jsonrpc':'2.0','method':'notifications/initialized'},
        {'jsonrpc':'2.0','id':2,'method':'tools/list'},
        {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'statistics_status'}},
    ]
    stdout,stderr = process.communicate('\n'.join(json.dumps(m) for m in messages)+'\n',timeout=30)
    if process.returncode: raise AssertionError(stderr)
    replies = [json.loads(line) for line in stdout.splitlines()]
    check('MCP inherited stdio and handshake',len(replies)==3 and replies[0]['result']['serverInfo']['version']==VERSION)
    check('MCP exposes management tools',len(replies[1]['result']['tools'])==2)
    check('MCP correct isolated registration',replies[2]['result']['structuredContent']['pluginId']=='codex-native-stats@codex-stats' and replies[2]['result']['structuredContent']['enabled'])

try:
    setup = ROOT/'dist'/f'CodexStats-Setup-{VERSION}-windows-x64.exe'
    run([setup,'--silent','--isolated','--root',INSTALL,'--codex-home',HOME])
    check('real self-contained setup fresh install',installed_version()==VERSION)
    check('official CLI enabled plugin',config()['plugins']['codex-native-stats@codex-stats']['enabled'])
    check('unrelated model configuration preserved',config()['model']=='sentinel-model' and config()['model_providers']['sentinel']['base_url']=='http://127.0.0.1:1234/v1')
    protocol()
    cache_path = next((HOME/'plugins/cache').rglob('CodexStatsHost.exe'))
    cache_hash = digest(cache_path)
    loaded = hold_server()
    run([setup,'--silent','--isolated','--root',INSTALL,'--codex-home',HOME])
    check('same-version repeat install with MCP loaded',installed_version()==VERSION and digest(cache_path)==cache_hash and loaded.poll() is None)
    broken = OUT/'broken-payload';shutil.copytree(PAYLOAD,broken)
    (broken/'marketplace/plugins/codex-native-stats/runtime/plugin_server.py').write_text('corrupted',encoding='utf-8')
    before = digest(HOME/'config.toml')
    run([python,installer,'install','--payload',broken,'--root',INSTALL,'--codex-home',HOME,'--isolated'],expected=1)
    check('corruption rejected before changes',installed_version()==VERSION and digest(HOME/'config.toml')==before)
    future = OUT/'upgrade-payload';shutil.copytree(PAYLOAD,future)
    future_version = '3.0.1-test'
    (future/'VERSION').write_text(future_version+'\n',encoding='utf-8')
    manifest = future/'marketplace/plugins/codex-native-stats/.codex-plugin/plugin.json'
    data = json.loads(manifest.read_text(encoding='utf-8'));data['version']=future_version
    manifest.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
    hashes = {p.relative_to(future).as_posix():digest(p) for p in future.rglob('*') if p.is_file() and p.name!='files.json'}
    (future/'files.json').write_text(json.dumps(hashes),encoding='utf-8')
    run([python,installer,'install','--payload',future,'--root',INSTALL,'--codex-home',HOME,'--isolated'])
    loaded.wait(timeout=10)
    check('upgrade released owned MCP cache',loaded.poll() is not None)
    check('versioned upgrade switched pointer',installed_version()==future_version and (INSTALL/'versions'/VERSION).is_dir())
    check('upgrade registration version',any((HOME/'plugins/cache').glob('codex-stats/codex-native-stats/'+future_version)))
    sample = HOME/'plugins/state/codex-native-stats/speed-samples.json'
    sample.parent.mkdir(parents=True,exist_ok=True);sample.write_bytes(synthetic)
    loaded = hold_server()
    run([python,installer,'uninstall','--root',INSTALL,'--silent'])
    loaded.wait(timeout=10)
    check('uninstall released owned MCP cache',loaded.poll() is not None)
    check('uninstall removed only owned registrations','codex-native-stats@codex-stats' not in config().get('plugins',{}) and 'codex-stats' not in config().get('marketplaces',{}))
    check('uninstall preserved user data and samples',(HOME/'auth.json').read_bytes()==synthetic and (HOME/'chat-sentinel.jsonl').read_bytes()==synthetic and sample.read_bytes()==synthetic)
    deadline = time.monotonic()+25
    while INSTALL.exists() and time.monotonic()<deadline: time.sleep(.5)
    check('uninstall removed owned runtime',not INSTALL.exists())
    check('production configuration unchanged',digest(production_config)==production_before)
    report['passed']=True
finally:
    report['productionTouched']=digest(production_config)!=production_before
    (OUT/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Report: '+str(OUT/'report.json'))
