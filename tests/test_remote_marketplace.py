"""Optional post-push GitHub marketplace smoke test with isolated CODEX_HOME."""
from pathlib import Path
import hashlib, importlib.util, json, os, subprocess, time, tomllib

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'validation'/('remote-'+str(int(time.time())))
HOME = OUT/'codex-home';HOME.mkdir(parents=True)
INSTALL = OUT/'install'
VERSION = (ROOT/'VERSION').read_text().strip()
PAYLOAD = ROOT/'build/payload'
spec = importlib.util.spec_from_file_location('stats_installer',ROOT/'installer/install.py')
installer = importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
env=os.environ.copy();env.update(CODEX_HOME=str(HOME),CODEX_STATS_INSTALL_ROOT=str(INSTALL),
    CODEX_STATS_PLUGIN_NO_AUTOSTART='1',PYTHONIOENCODING='utf-8')
file=Path.home()/'.codex/config.toml'
before=hashlib.sha256(file.read_bytes()).hexdigest() if file.exists() else None
report={'checks':{}}

def run(args):
    result=subprocess.run(list(map(str,args)),env=env,capture_output=True,encoding='utf-8',
                          timeout=150,creationflags=0x08000000)
    if result.returncode:raise AssertionError(result.stdout+result.stderr)
    return result.stdout

def check(name,value):
    report['checks'][name]=bool(value)
    if not value:raise AssertionError(name)
    print('PASS '+name,flush=True)

try:
    run([ROOT/'dist'/f'CodexStats-Setup-{VERSION}-windows-x64.exe','--silent','--isolated','--root',INSTALL,'--codex-home',HOME])
    command=installer.find_cli()
    run([command,'plugin','marketplace','remove','codex-stats'])
    added=json.loads(run([command,'plugin','marketplace','add','wangding0610/codex-native-stats','--ref','main','--json']))
    check('GitHub marketplace downloaded',added['marketplaceName']=='codex-stats' and Path(added['installedRoot']).is_dir())
    run([command,'plugin','add','codex-native-stats@codex-stats','--json'])
    cfg=tomllib.loads((HOME/'config.toml').read_text(encoding='utf-8'))
    check('GitHub plugin registered and enabled',cfg['plugins']['codex-native-stats@codex-stats']['enabled'])
    host=next((HOME/'plugins/cache').rglob('CodexStatsHost.exe'))
    process=subprocess.run([str(host)],cwd=host.parents[2],env=env,
        input='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n{"jsonrpc":"2.0","id":2,"method":"tools/list"}\n',
        capture_output=True,text=True,encoding='utf-8',timeout=30,creationflags=0x08000000)
    replies=[json.loads(line) for line in process.stdout.splitlines()]
    check('GitHub-installed MCP runs with bundled runtime',process.returncode==0 and len(replies)==2 and replies[0]['result']['serverInfo']['version']==VERSION and len(replies[1]['result']['tools'])==2)
    run([PAYLOAD/'python/python.exe',PAYLOAD/'installer/install.py','uninstall','--root',INSTALL,'--silent'])
    deadline=time.monotonic()+25
    while INSTALL.exists() and time.monotonic()<deadline:time.sleep(.5)
    check('GitHub installation uninstalls cleanly',not INSTALL.exists() and 'codex-stats' not in tomllib.loads((HOME/'config.toml').read_text(encoding='utf-8')).get('marketplaces',{}))
    check('production configuration unchanged',(hashlib.sha256(file.read_bytes()).hexdigest() if file.exists() else None)==before)
    report['passed']=True
finally:
    (OUT/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Report: '+str(OUT/'report.json'))
