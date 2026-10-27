import urllib.request, pathlib, hashlib, json, datetime, concurrent.futures, zipfile
root=pathlib.Path(__file__).resolve().parents[1]
(root/'data/raw').mkdir(parents=True,exist_ok=True)
def download(month):
 name=f'{month}-capitalbikeshare-tripdata.zip'; url='https://s3.amazonaws.com/capitalbikeshare-data/'+name
 path=root/'data/raw'/name
 if not path.exists():
  with urllib.request.urlopen(url,timeout=120) as r, path.with_suffix('.part').open('wb') as f:
   while chunk:=r.read(1024*1024): f.write(chunk)
  path.with_suffix('.part').rename(path)
 with zipfile.ZipFile(path) as z:
  assert z.testzip() is None
  files=[{'name':i.filename,'bytes':i.file_size} for i in z.infolist() if i.filename.endswith('.csv') and not i.filename.startswith('__MACOSX/')]
 result={'month':month,'url':url,'retrieved_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'csv_members':files}
 print(json.dumps(result),flush=True); return result
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool: records=list(pool.map(download,['202606','202607','202608']))
(root/'data/source_manifest.json').write_text(json.dumps(records,indent=2))

