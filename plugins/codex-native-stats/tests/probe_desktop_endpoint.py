"""Inspect the endpoint from Explorer's desktop launch context."""
import json,os,sys,time
from pathlib import Path
import psutil
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
import official_adapter as adapter

files=adapter.endpoint_port_files(adapter.BROWSER)
exists=[file.is_file() for file in files]
port=adapter.debug_port()
parent=psutil.Process().parent()
result={'pid':os.getpid(),'parentName':parent.name() if parent else None,'portFiles':[str(file) for file in files],'fileExists':exists,'port':port,'diagnostic':adapter._endpoint_diagnostic,'checkedAt':time.time()}
result['passed']=port is not None and result['diagnostic']['reason']=='ready'
Path(sys.argv[1]).write_text(json.dumps(result,indent=2),encoding='utf-8')
