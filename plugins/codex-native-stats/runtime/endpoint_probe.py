"""Validate the official loopback endpoint in a fresh, short-lived process."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import official_adapter as adapter

if __name__=='__main__':
    port=adapter.debug_port(Path(sys.argv[1]))
    print(json.dumps({'port':port,'diagnostic':adapter._endpoint_diagnostic}),flush=True)
