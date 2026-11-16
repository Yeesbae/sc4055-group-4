"""Acquire official Cboe bytes; redistribution is not assumed."""
import argparse,hashlib,json,urllib.request
from datetime import datetime,timezone
from pathlib import Path
URL='https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv'

def download(output):
    path=Path(output);path.parent.mkdir(parents=True,exist_ok=True)
    with urllib.request.urlopen(URL,timeout=45) as r:
        b=r.read();resolved=r.url;headers=dict(r.headers)
    path.write_bytes(b)
    info={'source_url':URL,'resolved_url':resolved,'downloaded_utc':datetime.now(timezone.utc).isoformat(),
          'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'response_headers':headers,
          'redistribution':'Raw series excluded from deliverable ZIP; reacquire from official source. No open-data license asserted.'}
    path.with_suffix('.manifest.json').write_text(json.dumps(info,indent=2))
    print(json.dumps({k:info[k] for k in ['source_url','sha256','bytes']}))
    return path

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='private_data/VIX_History.csv');a=p.parse_args();download(a.output)
