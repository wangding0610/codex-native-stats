"""Open the official Store executable with the plugin adapter when enabled."""
from pathlib import Path
import subprocess,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import official_adapter as adapter
from plugin_server import ensure_adapter

if adapter.registered():ensure_adapter(focus=True)
else:
    adapter.STATE.mkdir(parents=True,exist_ok=True)
    (adapter.STATE/'cancel.signal').touch()
    if adapter.official_pids():adapter.focus_official()
    else:subprocess.Popen(['explorer.exe','shell:AppsFolder\\'+adapter.APP_ID])
