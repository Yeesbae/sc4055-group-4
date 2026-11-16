"""Freeze the reviewed Phase-3 deliverable with byte checksums."""
import hashlib,json,zipfile,gzip
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]

def main():
    assert (ROOT/'validation/test_results.txt').read_text().rstrip().endswith('OK')
    assert json.loads((ROOT/'validation/fresh_directory_reproduction.json').read_text())['all_equal']
    assert json.loads((ROOT/'validation/source_preservation.json').read_text())['all_unchanged']
    assert json.loads((ROOT/'validation/visual_review.json').read_text())['all_pages_rendered_and_visually_reviewed']
    for p in (ROOT/'figures').glob('*.png'):Image.open(p).verify()
    for p in (ROOT/'results').glob('*.gz'):gzip.decompress(p.read_bytes())
    pdf=ROOT/'report/SC4055_V3_Phase3_Nine_State_Validation_Report.pdf';b=pdf.read_bytes();assert b.startswith(b'%PDF-') and b'%%EOF' in b[-50:]
    def included(p):return p.is_file() and '__pycache__' not in p.parts and 'private_data' not in p.parts and p.suffix!='.pyc' and p.name!='CHECKSUMS.sha256'
    files=sorted(p for p in ROOT.rglob('*') if included(p));assert not any(p.name=='VIX_History.csv' for p in files)
    checks={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (ROOT/'CHECKSUMS.sha256').write_text('\n'.join(h+'  '+p for p,h in checks.items())+'\n')
    archive=ROOT.parent/'SC4055_V3_Phase3_Research_Package.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in files+[ROOT/'CHECKSUMS.sha256']:z.write(p,ROOT.name+'/'+p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for p,h in checks.items():assert hashlib.sha256(z.read(ROOT.name+'/'+p)).hexdigest()==h
    print(json.dumps({'archive':str(archive),'files':len(files)+1,'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}))

if __name__=='__main__':main()
