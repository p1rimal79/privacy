"""Collect rights-filtered research unknowns; source labels are NOT presence/absence truth."""
import argparse, asyncio, hashlib, json, time
from pathlib import Path
import httpx

def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--known',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    known=[json.loads(s) for s in a.known.read_text().splitlines()]
    known_ids={r['inaturalist_taxon_id'] for r in known};known_hashes={r['sha256'] for r in known}
    known_groups={r['session_group']:r['split'] for r in known}
    observer_splits={r['observer_id']:r['split'] for r in known if r['split']=='observer_holdout'}
    a.output.mkdir(parents=True,exist_ok=True);(a.output/'images').mkdir(exist_ok=True)
    records={}
    manifest=a.output/'manifest.jsonl'
    if manifest.exists():records={r['photo_id']:r for r in map(json.loads,manifest.read_text().splitlines())}
    with httpx.Client(timeout=25) as client:
        for category,tid,pages in [('other_fungi',47170,10),('plants',47126,10)]:
            for page in range(1,pages+1):
                time.sleep(1.1)
                try:
                    response=client.get('https://api.inaturalist.org/v1/observations',params={'taxon_id':tid,'place_id':8860,'quality_grade':'research','license':'cc0,cc-by','photo_license':'cc0,cc-by','photos':'true','captive':'false','per_page':40,'page':page,'order_by':'id','order':'desc'})
                    response.raise_for_status();observations=response.json()['results']
                except Exception as e:print(category,page,type(e).__name__,flush=True);continue
                candidates=[]
                for o in observations:
                    taxon=o.get('taxon',{});ancestors=set(taxon.get('ancestor_ids',[]))|{taxon.get('id')}
                    if ancestors & known_ids or o.get('license_code') not in {'cc0','cc-by'} or o.get('flags') or o.get('captive'):continue
                    photo=next((v for v in o.get('photos',[]) if v.get('license_code') in {'cc0','cc-by'}),None)
                    if not photo or photo['id'] in records:continue
                    author=str(o['user']['id']);group=author+':'+(o.get('observed_on') or str(o['id']))
                    n=int(sha(group.encode())[:8],16)%100
                    hold=int(sha(('observer:'+author).encode())[:8],16)%13==0 or author in observer_splits
                    split='observer_holdout' if hold else known_groups.get(group,'train' if n<70 else 'validation' if n<85 else 'test')
                    candidates.append({'photo_id':photo['id'],'observation_id':o['id'],'observer_id':author,'session_group':group,'split_group':group,'split':split,
                        'category':category,'source_taxon_id':taxon.get('id'),'source_taxon_name':taxon.get('name'),'taxon_id':'unknown',
                        'label_basis':'source_taxon_outside_known_set_unreviewed','expert_verified':False,'known_mushroom_absence_verified':False,
                        'photo_license':photo['license_code'],'observation_license':o['license_code'],'country':'UA',
                        'attribution':photo.get('attribution') or o['user'].get('login'),'source_url':f"https://www.inaturalist.org/observations/{o['id']}",
                        'download_url':photo['url'].replace('/square.','/medium.'),'relative_path':f"images/{photo['id']}.jpg"})
                async def fetch():
                    sem=asyncio.Semaphore(8)
                    async with httpx.AsyncClient(timeout=15) as media:
                        async def one(r):
                            async with sem:
                                try:
                                    path=a.output/r['relative_path']
                                    if path.exists():b=path.read_bytes()
                                    else:
                                        response=await asyncio.wait_for(media.get(r['download_url']),18);response.raise_for_status();b=response.content
                                    if not b.startswith(b'\xff\xd8') or len(b)>4*1024**2 or sha(b) in known_hashes:return None
                                    tmp=path.with_suffix('.tmp');tmp.write_bytes(b);tmp.replace(path)
                                    r['sha256']=sha(b);r['size_bytes']=len(b);return r
                                except Exception:return None
                        return await asyncio.gather(*(one(r) for r in candidates))
                for r in asyncio.run(fetch()):
                    if r:records[r['photo_id']]=r
                manifest.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in records.values()))
                print(category,page,'total',len(records),flush=True)
    from PIL import Image
    unique={};bad=[]
    for r in records.values():
        try:
            with Image.open(a.output/r['relative_path']) as im:
                assert not im.getexif().get(34853);im.load()
            unique.setdefault(r['sha256'],r)
        except Exception:bad.append(r['photo_id'])
    manifest.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in unique.values()))
    (a.output/'report.json').write_text(json.dumps({'photos':len(unique),'bad':bad,'expert_verified':0,'negative_presence_verified':0,'purpose':'research unknown class, not certified detector negatives'},indent=2)+'\n')
if __name__=='__main__':main()
