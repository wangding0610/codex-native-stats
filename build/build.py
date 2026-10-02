"""Build a self-contained Windows x64 release using official, pinned runtimes."""
from pathlib import Path
import gzip, hashlib, json, os, shutil, subprocess, sys, urllib.request, zipfile

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT/'build/cache'
PAYLOAD = ROOT/'build/payload'
DIST = ROOT/'dist'
PYTHON = '3.13.16'
NODE = '22.23.3'
PACKAGES = {'psutil':'7.2.2','websocket-client':'1.8.0','pywin32':'312'}

def fetch(url):
    data = urllib.request.urlopen(url,timeout=60).read()
    return gzip.decompress(data) if data[:2]==b'\x1f\x8b' else data

def download(url, name, digest=None):
    CACHE.mkdir(parents=True,exist_ok=True)
    file = CACHE/name
    if not file.exists(): file.write_bytes(fetch(url))
    actual = hashlib.sha256(file.read_bytes()).hexdigest()
    if digest and actual != digest: raise RuntimeError('SHA256 mismatch: '+name)
    return file, actual

def clean(directory):
    target = directory.resolve()
    if not target.is_relative_to(ROOT) or target==ROOT: raise ValueError('Unsafe cleanup target')
    if target.exists(): shutil.rmtree(target)
    target.mkdir(parents=True)

def compile_cs(source, output, target='exe', extra=()):
    compiler = Path(os.environ.get('WINDIR','C:/Windows'))/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    subprocess.run([str(compiler),'/nologo','/optimize+','/codepage:65001','/target:'+target,'/out:'+str(output),
                    *extra,str(ROOT/'build'/source)],check=True)

def main():
    version = (ROOT/'VERSION').read_text().strip()
    clean(PAYLOAD); DIST.mkdir(exist_ok=True)
    dependencies = []
    py_name = f'python-{PYTHON}-embed-amd64.zip'
    py_url = f'https://www.python.org/ftp/python/{PYTHON}/{py_name}'
    # CPython release metadata doesn't publish SHA256 in the HTML. HTTPS from
    # python.org plus a checked-in lock pins the exact bytes used by this build.
    lock_file = ROOT/'build/dependencies.lock.json'
    lock = json.loads(lock_file.read_text()) if lock_file.exists() else {}
    py_file, py_hash = download(py_url,py_name,lock.get(py_name))
    dependencies.append({'name':'CPython','version':PYTHON,'url':py_url,'sha256':py_hash})
    with zipfile.ZipFile(py_file) as archive: archive.extractall(PAYLOAD/'python')
    pth = PAYLOAD/'python/python313._pth'
    pth.write_text('python313.zip\n.\nLib/site-packages\nLib/site-packages/win32\nLib/site-packages/win32/lib\nLib/site-packages/Pythonwin\nimport site\n',encoding='utf-8')
    (PAYLOAD/'python/Lib/site-packages').mkdir(parents=True)
    for package, pinned in PACKAGES.items():
        data = json.loads(fetch(f'https://pypi.org/pypi/{package}/{pinned}/json'))
        choices = [f for f in data['urls'] if f['filename'].endswith('.whl') and
                   (f['filename'].endswith('py3-none-any.whl') or
                    ('win_amd64.whl' in f['filename'] and ('cp313-cp313-' in f['filename'] or 'cp37-abi3-' in f['filename'])))]
        if len(choices)!=1: raise RuntimeError('Ambiguous wheel for '+package)
        wheel = choices[0]
        file, digest = download(wheel['url'],wheel['filename'],wheel['digests']['sha256'])
        dependencies.append({'name':package,'version':pinned,'url':wheel['url'],'sha256':digest})
        with zipfile.ZipFile(file) as archive: archive.extractall(PAYLOAD/'python/Lib/site-packages')
    # Embedded Python doesn't reliably process pywin32 bootstrap .pth files.
    # Its two support DLLs must be next to the interpreter for standard imports.
    for file in (PAYLOAD/'python/Lib/site-packages/pywin32_system32').glob('*.dll'):
        shutil.copyfile(file,PAYLOAD/'python'/file.name)
    node_name = f'node-v{NODE}-win-x64.zip'
    node_base = f'https://nodejs.org/dist/v{NODE}/'
    expected = lock.get(node_name)
    if not expected:
        sums = fetch(node_base+'SHASUMS256.txt').decode('ascii')
        expected = next(line.split()[0] for line in sums.splitlines() if line.split()[-1]==node_name)
    node_file,node_hash = download(node_base+node_name,node_name,expected)
    dependencies.append({'name':'Node.js','version':NODE,'url':node_base+node_name,'sha256':node_hash})
    (PAYLOAD/'node').mkdir()
    with zipfile.ZipFile(node_file) as archive:
        for name in ['node.exe','LICENSE','README.md']:
            (PAYLOAD/'node'/name).write_bytes(archive.read(f'node-v{NODE}-win-x64/'+name))
    market = PAYLOAD/'marketplace'
    shutil.copytree(ROOT/'plugins',market/'plugins',ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.bak','tests'))
    shutil.copytree(ROOT/'.agents',market/'.agents')
    for name in ['LICENSE','README.md','THIRD_PARTY_NOTICES.md']:
        shutil.copyfile(ROOT/name,PAYLOAD/name)
    shutil.copyfile(ROOT/'VERSION',PAYLOAD/'VERSION')
    shutil.copytree(ROOT/'installer',PAYLOAD/'installer',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    (PAYLOAD/'host').mkdir()
    host = ROOT/'plugins/codex-native-stats/runtime/bin/CodexStatsHost.exe'
    host.parent.mkdir(exist_ok=True)
    compile_cs('Host.cs',host,extra=['/reference:System.Windows.Forms.dll'])
    shutil.copyfile(host,PAYLOAD/'host/CodexStatsHost.exe')
    (market/'plugins/codex-native-stats/runtime/bin').mkdir(exist_ok=True)
    shutil.copyfile(host,market/'plugins/codex-native-stats/runtime/bin/CodexStatsHost.exe')
    compile_cs('Host.cs',PAYLOAD/'host/CodexStats.exe','winexe',['/reference:System.Windows.Forms.dll'])
    compile_cs('Cleanup.cs',PAYLOAD/'host/CodexStatsCleanup.exe','winexe')
    (PAYLOAD/'DEPENDENCIES.json').write_text(json.dumps(dependencies,indent=2),encoding='utf-8')
    lock_file.write_text(json.dumps({Path(d['url']).name:d['sha256'] for d in dependencies},indent=2)+'\n',encoding='utf-8')
    # A real embedded-runtime import check before producing any release artifact.
    smoke_env = os.environ.copy(); smoke_env['PYTHONDONTWRITEBYTECODE']='1'
    subprocess.run([str(PAYLOAD/'python/python.exe'),'-c',
                    'import psutil,websocket,win32com.client,win32api,tomllib;print("Embedded runtime imports OK")'],check=True,env=smoke_env)
    subprocess.run([str(PAYLOAD/'node/node.exe'),'--disable-warning=ExperimentalWarning','-e',
                    'const {DatabaseSync}=require("node:sqlite"); const d=new DatabaseSync(":memory:"); console.log("Bundled SQLite OK"); d.close()'],check=True)
    files = {p.relative_to(PAYLOAD).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(PAYLOAD.rglob('*')) if p.is_file()}
    (PAYLOAD/'files.json').write_text(json.dumps(files,indent=2),encoding='utf-8')
    zip_path = DIST/f'CodexStats-{version}-windows-x64.zip'
    with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for p in sorted(PAYLOAD.rglob('*')):
            if p.is_file(): archive.write(p,p.relative_to(PAYLOAD).as_posix())
    setup = DIST/f'CodexStats-Setup-{version}-windows-x64.exe'
    compile_cs('Setup.cs',setup,'winexe',['/reference:System.IO.Compression.dll',
               '/reference:System.IO.Compression.FileSystem.dll','/reference:System.Windows.Forms.dll',
               f'/resource:{zip_path},payload.zip'])
    (DIST/'SHA256SUMS.txt').write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name
                                            for p in [setup,zip_path])+'\n',encoding='ascii')
    print('Built '+str(setup))

if __name__=='__main__': main()
