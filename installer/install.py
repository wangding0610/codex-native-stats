"""Per-user, versioned installation. Never modifies the official Store package."""
from pathlib import Path
import argparse, ctypes, hashlib, json, os, re, shutil, subprocess, sys, tempfile, time, tomllib, uuid, winreg

PRODUCT = 'CodexNativeStats'
PLUGIN = 'codex-native-stats@codex-stats'
REGISTRY = r'Software\CodexNativeStats'
UNINSTALL = r'Software\Microsoft\Windows\CurrentVersion\Uninstall\CodexNativeStats'
NO_WINDOW = 0x08000000

def atomic(file, content):
    file.parent.mkdir(parents=True, exist_ok=True)
    next_file = file.with_suffix('.next')
    next_file.write_text(content, encoding='utf-8')
    os.replace(next_file, file)

def safe_child(root, child):
    root, child = root.resolve(), child.resolve()
    if child == root or not child.is_relative_to(root):
        raise ValueError('Refusing filesystem operation outside the installation directory')
    return child

def remove_child(root, child):
    child = safe_child(root, child)
    if child.is_dir(): shutil.rmtree(child)
    elif child.exists(): child.unlink()

def find_cli(explicit=None):
    if explicit:
        file = Path(explicit).resolve()
        if not file.is_file(): raise RuntimeError('Specified Codex CLI does not exist')
        return str(file)
    candidates = []
    for root in [Path.home()/'AppData/Local/OpenAI/Codex/bin',
                 Path.home()/'AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/OpenAI/Codex/bin']:
        candidates.extend(root.glob('*/codex.exe'))
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    command = shutil.which('codex.exe')
    if command: candidates.append(Path(command))
    for candidate in candidates:
        if candidate.is_file(): return str(candidate)
    raise RuntimeError('找不到 Codex CLI。请先安装并启动微软商店版 Codex 一次，再重新运行安装器。')

def cli(command, home, *args):
    env = os.environ.copy(); env['CODEX_HOME'] = str(home)
    result = subprocess.run([command, 'plugin', *args], env=env, capture_output=True,
                            text=True, encoding='utf-8', timeout=120, creationflags=NO_WINDOW)
    if result.returncode:
        raise RuntimeError('Codex plugin command failed: ' + result.stderr[-2000:])
    return result.stdout

def configuration(home):
    file = home/'config.toml'
    return tomllib.loads(file.read_text(encoding='utf-8-sig')) if file.exists() else {}

def verify_payload(payload):
    manifest = json.loads((payload/'files.json').read_text(encoding='utf-8'))
    for relative, digest in manifest.items():
        file = safe_child(payload, payload/relative)
        if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != digest:
            raise RuntimeError('Payload integrity check failed: ' + relative)
    version = (payload/'VERSION').read_text().strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?', version):
        raise RuntimeError('Invalid package version')
    return version

def stop_backend(home):
    """Signal only our controller; never kill its official-App children."""
    state = home/'plugins/state/codex-native-stats'
    state.mkdir(parents=True, exist_ok=True)
    (state/'cancel.signal').touch()
    try:
        status = json.loads((state/'status.json').read_text(encoding='utf-8'))
        import psutil
        process = psutil.Process(status.get('pid'))
        args = process.cmdline()
        if not any(a.replace('\\','/').endswith('/runtime/official_adapter.py') for a in args): return
        try: process.wait(timeout=6)
        except psutil.TimeoutExpired: raise RuntimeError('请正常退出统计后台后重试；安装器不会结束官方客户端。')
    except (FileNotFoundError, ValueError, TypeError): pass
    except ImportError: pass
    except psutil.NoSuchProcess: pass

def release_mcp_cache(home):
    import psutil
    cache = (home/'plugins/cache/codex-stats/codex-native-stats').resolve()
    for process in psutil.process_iter(['name','cmdline']):
        try:
            args = process.info['cmdline'] or []
            if (process.info['name'] or '').lower() not in ['python.exe','pythonw.exe']: continue
            if any(Path(a).resolve().is_relative_to(cache) and Path(a).name=='plugin_server.py' for a in args[1:] if a.endswith('.py')):
                process.terminate(); process.wait(timeout=5)
        except (psutil.NoSuchProcess, psutil.AccessDenied): pass

def shortcut_target(file):
    import pythoncom
    from win32com.shell import shell
    link = pythoncom.CoCreateInstance(shell.CLSID_ShellLink,None,pythoncom.CLSCTX_INPROC_SERVER,shell.IID_IShellLink)
    link.QueryInterface(pythoncom.IID_IPersistFile).Load(str(file))
    return Path(link.GetPath(shell.SLGP_RAWPATH)[0]).resolve()

def cache_official_icon(root, version):
    """Keep a local icon so Store package version paths cannot break shortcuts."""
    destination = safe_child(root,root/'versions'/version/'host/official-app.ico')
    script = '[Console]::OutputEncoding=[Text.Encoding]::UTF8; (Get-AppxPackage -Name OpenAI.Codex | Sort-Object Version -Descending | Select-Object -First 1).InstallLocation'
    try:
        result = subprocess.run(['powershell.exe','-NoProfile','-Command',script],
                                capture_output=True,encoding='utf-8',timeout=15,
                                creationflags=NO_WINDOW,check=True)
        location = result.stdout.strip()
        if location:
            package = Path(location)
            if package.parent.name.lower()=='windowsapps' and package.name.lower().startswith('openai.codex_'):
                for name in ['chatgpt-app-dark.ico','icon-chatgpt.ico','chatgpt-app-light.ico']:
                    source = package/'app/resources'/name
                    if source.is_file() and source.read_bytes()[:4]==b'\x00\x00\x01\x00':
                        destination.parent.mkdir(parents=True,exist_ok=True)
                        shutil.copyfile(source,destination)
                        break
    except (OSError,subprocess.SubprocessError): pass
    return destination if destination.is_file() else None

def save_shortcut(file, target, argument, directory, icon=None):
    import pythoncom
    from win32com.shell import shell,shellcon
    link = pythoncom.CoCreateInstance(shell.CLSID_ShellLink,None,pythoncom.CLSCTX_INPROC_SERVER,shell.IID_IShellLink)
    link.SetPath(str(target)); link.SetArguments(argument); link.SetWorkingDirectory(str(directory))
    link.SetShowCmd(7); link.SetDescription('官方 Codex 客户端与本地输入栏统计')
    if icon: link.SetIconLocation(str(icon),0)
    # IPersistFile uses Unicode paths, unlike WScript.Save on some ANSI locales.
    link.QueryInterface(pythoncom.IID_IPersistFile).Save(str(file),0)
    shell.SHChangeNotify(shellcon.SHCNE_UPDATEITEM,shellcon.SHCNF_PATHW,str(file),None)

def integrations(root, version, home):
    from win32com.shell import shell, shellcon
    shortcuts = []
    desktop = Path(shell.SHGetFolderPath(0,shellcon.CSIDL_DESKTOPDIRECTORY,0,0))
    programs = Path(shell.SHGetFolderPath(0,shellcon.CSIDL_PROGRAMS,0,0))/'Codex 输入栏统计'
    programs.mkdir(parents=True, exist_ok=True)
    icon = cache_official_icon(root,version)
    for file, argument in [(desktop/'Codex 官方版（输入栏统计）.lnk','--launch'),
                           (programs/'Codex 官方版（输入栏统计）.lnk','--launch'),
                           (programs/'卸载 Codex 输入栏统计.lnk','--uninstall')]:
        if file.exists():
            if shortcut_target(file) != (root/'CodexStats.exe').resolve():
                raise RuntimeError('快捷方式名称已由其他应用使用：'+file.name)
        save_shortcut(file,root/'CodexStats.exe',argument,root,icon); shortcuts.append(str(file))
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY) as key:
        winreg.SetValueEx(key, 'InstallRoot', 0, winreg.REG_SZ, str(root))
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL) as key:
        for name, value in {'DisplayName':'Codex 输入栏统计', 'DisplayVersion':version,
                            'Publisher':'wangding0610', 'InstallLocation':str(root),
                            'UninstallString':f'"{root / "CodexStats.exe"}" --uninstall',
                            'URLInfoAbout':'https://github.com/wangding0610/codex-native-stats'}.items():
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
        if icon: winreg.SetValueEx(key,'DisplayIcon',0,winreg.REG_SZ,str(icon)+',0')
        for name in ['NoModify','NoRepair']: winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, 1)
    return shortcuts

def install(args):
    payload, root = Path(args.payload).resolve(), Path(args.root).resolve()
    version = verify_payload(payload)
    home = Path(args.codex_home or os.environ.get('CODEX_HOME',str(Path.home()/'.codex'))).resolve()
    command = find_cli(args.cli)
    marker = root/'install.json'
    previous = json.loads(marker.read_text(encoding='utf-8')) if marker.exists() else None
    if root.exists() and any(root.iterdir()) and not previous:
        raise RuntimeError('安装目录不是本插件创建的空目录，请选择其他目录。')
    if previous and Path(previous['codexHome']).resolve()!=home:
        raise RuntimeError('This installation belongs to a different CODEX_HOME')
    if not args.isolated:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY) as key:
            try: registered_root = Path(winreg.QueryValueEx(key,'InstallRoot')[0]).resolve()
            except FileNotFoundError: registered_root = root
            if registered_root != root: raise RuntimeError('已有其他目录的安装，请先卸载或使用原目录升级。')
    home.mkdir(parents=True, exist_ok=True)
    cfg = configuration(home)
    if 'codex-native-stats@personal' in cfg.get('plugins',{}):
        raise RuntimeError('检测到旧 personal 统计插件。请先保存任务、正常退出 Codex，并移除旧 personal 插件，再安装公开发行版。')
    existing_market = cfg.get('marketplaces',{}).get('codex-stats')
    dest = safe_child(root, root/'versions'/version)
    market = dest/'marketplace'
    if existing_market and not previous:
        raise RuntimeError('已有 codex-stats 市场。请先从插件管理中移除该市场，再安装 Windows 发行包。')
    root.mkdir(parents=True, exist_ok=True)
    stage = safe_child(root, root/('staging-'+str(os.getpid())))
    old_cfg_file = home/'config.toml'
    old_cfg = old_cfg_file.read_bytes() if old_cfg_file.exists() else None
    config_after_cli = None
    new_dest = not dest.exists()
    try:
        if new_dest:
            shutil.copytree(payload, stage)
            dest.parent.mkdir(parents=True, exist_ok=True)
            os.replace(stage, dest)
        else: verify_payload(dest)
        if previous: stop_backend(home)
        # Do not re-copy a loaded same-version cache: Windows locks its cwd.
        if not previous or previous['version'] != version:
            if previous: release_mcp_cache(home)
            if previous and 'codex-stats' in configuration(home).get('marketplaces',{}):
                cli(command,home,'marketplace','remove','codex-stats')
                config_after_cli = old_cfg_file.read_bytes()
            cli(command, home, 'marketplace','add',str(market),'--json')
            config_after_cli = old_cfg_file.read_bytes()
            cli(command, home, 'add',PLUGIN,'--json')
            config_after_cli = old_cfg_file.read_bytes()
        shutil.copyfile(dest/'host/CodexStats.exe', root/'CodexStats.exe')
        links = [] if args.isolated else integrations(root,version,home)
        record = {'product':PRODUCT,'version':version,'codexHome':str(home),
                  'shortcuts':links,'isolated':args.isolated}
        atomic(marker,json.dumps(record,ensure_ascii=False,indent=2))
        atomic(root/'current-version.txt',version+'\n')
    except Exception:
        # Restore only if no other writer changed configuration after our CLI call.
        if config_after_cli is not None and old_cfg_file.read_bytes()==config_after_cli:
            if old_cfg is None: old_cfg_file.unlink(missing_ok=True)
            else: old_cfg_file.write_bytes(old_cfg)
        if stage.exists(): remove_child(root,stage)
        if new_dest and dest.exists(): remove_child(root,dest)
        raise
    print(json.dumps({'installed':True,'version':version,'root':str(root),'isolated':args.isolated},ensure_ascii=False))

def uninstall(args):
    root = Path(args.root).resolve(); marker = root/'install.json'
    if not marker.exists(): raise RuntimeError('This directory is not an installed Codex Stats package')
    record = json.loads(marker.read_text(encoding='utf-8'))
    if record.get('product') != PRODUCT: raise RuntimeError('Invalid installation ownership marker')
    if not record.get('isolated') and not args.silent:
        if ctypes.windll.user32.MessageBoxW(None,'卸载输入栏统计？\n保留官方客户端、聊天、登录和统计样本。','Codex 输入栏统计',0x21)!=1: return
    home = Path(record['codexHome']).resolve(); command = find_cli(args.cli)
    cfg = configuration(home)
    # Let the official CLI remove only this plugin's registration/cache.
    release_mcp_cache(home)
    if PLUGIN in cfg.get('plugins',{}): cli(command,home,'remove',PLUGIN)
    stop_backend(home)
    if 'codex-stats' in configuration(home).get('marketplaces',{}):
        cli(command,home,'marketplace','remove','codex-stats')
    if not record.get('isolated'):
        for entry in record.get('shortcuts',[]):
            file = Path(entry)
            if file.is_file() and shortcut_target(file)==root/'CodexStats.exe':
                file.unlink()
                if file.parent.name=='Codex 输入栏统计' and not any(file.parent.iterdir()): file.parent.rmdir()
        for path in [UNINSTALL, REGISTRY]:
            try: winreg.DeleteKey(winreg.HKEY_CURRENT_USER,path)
            except FileNotFoundError: pass
    # Run an independent native helper so no installed Python/DLL remains open.
    # It checks this ownership marker and removes only versions + our launcher.
    for name in ['versions','CodexStats.exe']: safe_child(root,root/name)
    cleanup_source = root/'versions'/record['version']/'host/CodexStatsCleanup.exe'
    cleanup = Path(tempfile.gettempdir())/('CodexStatsCleanup-'+uuid.uuid4().hex+'.exe')
    shutil.copyfile(cleanup_source,cleanup)
    atomic(root/'uninstall-pending.txt','CodexNativeStats\n'+str(root))
    marker.unlink(); (root/'current-version.txt').unlink(missing_ok=True)
    subprocess.Popen([str(cleanup),str(root),str(os.getpid())],cwd=Path.home(),
                     stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL,creationflags=NO_WINDOW)
    print('Codex Stats uninstalled; official App and user data preserved.')

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='action',required=True)
    for action in ['install','uninstall']:
        command = sub.add_parser(action)
        command.add_argument('--root',default=str(Path.home()/'CodexNativeStats'))
        command.add_argument('--cli'); command.add_argument('--silent',action='store_true')
        if action=='install':
            command.add_argument('--payload',required=True); command.add_argument('--codex-home')
            command.add_argument('--isolated',action='store_true',help='No registry, shortcuts or App activation; for validation only')
    args = parser.parse_args()
    kernel = ctypes.windll.kernel32; kernel.CreateMutexW.restype = ctypes.c_void_p
    root_digest = hashlib.sha256(str(Path(args.root).resolve()).casefold().encode()).hexdigest()[:24]
    mutex = kernel.CreateMutexW(None,True,'Local\\CodexStatsSetup-'+root_digest)
    if kernel.GetLastError()==183: raise RuntimeError('Another installer is running for this directory')
    try: globals()[args.action](args)
    finally:
        kernel.ReleaseMutex(ctypes.c_void_p(mutex)); kernel.CloseHandle(ctypes.c_void_p(mutex))

if __name__=='__main__':
    try: main()
    except Exception as error:
        print(str(error),file=sys.stderr); sys.exit(1)
