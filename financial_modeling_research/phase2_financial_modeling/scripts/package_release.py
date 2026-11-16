"""Freeze the research deliverable, excluding private data and interpreter caches."""
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def included(p):
    return p.is_file() and '__pycache__' not in p.parts and 'private_data' not in p.parts and p.suffix!='.pyc' and p.name!='CHECKSUMS.sha256'


def main():
    forecast=json.loads((ROOT/'validation/forecast_ledger_integrity.json').read_text())
    repro=json.loads((ROOT/'validation/fresh_directory_reproduction.json').read_text())
    preservation=json.loads((ROOT/'validation/source_preservation.json').read_text())
    assert forecast['roundtrip_verified'] and repro['all_compared_outputs_identical'] and repro['tests_passed']
    assert preservation['all_unchanged']
    assert (ROOT/'validation/test_results.txt').read_text().rstrip().endswith('OK')
    files=sorted(p for p in ROOT.rglob('*') if included(p))
    assert not any(p.name=='VIX_History.csv' for p in files)
    (ROOT/'CHECKSUMS.sha256').write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(ROOT).as_posix() for p in files)+'\n')
    out=ROOT.parent/'SC4055_V3_Phase2_Research_Package.zip'
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in files+[ROOT/'CHECKSUMS.sha256']:z.write(p,ROOT.name+'/'+p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None
        assert len(z.namelist())==len(files)+1
    print(json.dumps({'zip':str(out),'files':len(files)+1,'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}))


if __name__=='__main__':main()
