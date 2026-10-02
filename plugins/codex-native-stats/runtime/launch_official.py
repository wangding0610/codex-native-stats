"""Open the official Store executable with the plugin adapter when enabled."""
from pathlib import Path
import json,os,subprocess,sys
source=Path(__file__).resolve().parent
version=json.loads((source.parent/'.codex-plugin/plugin.json').read_text(encoding='utf-8'))['version']
home=Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex')))
cached=home/'plugins/cache/codex-stats/codex-native-stats'/version/'runtime'
# Desktop and MCP entry points must use the same adapter path, so a running
# controller is recognized rather than spawning an immediately exiting copy.
sys.path.insert(0,str(cached if (cached/'official_adapter.py').is_file() else source))
import official_adapter as adapter
from plugin_server import ensure_adapter

if adapter.registered():ensure_adapter(focus=True)
else:
    adapter.STATE.mkdir(parents=True,exist_ok=True)
    (adapter.STATE/'cancel.signal').touch()
    if adapter.official_pids():adapter.focus_official()
    else:subprocess.Popen(['explorer.exe','shell:AppsFolder\\'+adapter.APP_ID])
