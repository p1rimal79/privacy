"""Reproducible, bounded public-data collection. Never imports users' test photos.
Run: python3 tools/collect_reference.py --output ../data-work
API calls <= 1/second. Every image and observation needs CC0 or CC BY.
This is community-labelled research material, NOT expert ground truth.
"""
from pathlib import Path
import argparse, csv, io, json, hashlib, time, urllib.request, urllib.parse, zipfile, asyncio
try:
    import httpx
    HTTP = httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent":"MushroomFinderResearch/0.1.2"})
except ImportError:
    HTTP = None
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[1]
LICENSES = {'cc0', 'cc-by'}
ALIASES = {'Inosperma erubescens': 'Inocybe patouillardii', 'Hypholoma lateritium':'Hypholoma sublateritium'}
def digest(b): return hashlib.sha256(b).hexdigest()
def write(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n')
def get(url):
    for attempt in range(3):
        try:
            if HTTP is not None:
                response=HTTP.get(url);response.raise_for_status();return response.content
            req = urllib.request.Request(url, headers={'User-Agent':'MushroomFinderResearch/0.1.2 (public licensed data; no location retention)'})
            with urllib.request.urlopen(req, timeout=20) as r: return r.read()
        except Exception:
            if attempt == 2: raise
            time.sleep(2**attempt)
def api(url, params):
    time.sleep(1.05)
    return json.loads(get(url+'?'+urllib.parse.urlencode(params)))
def split(group):
    n=int(digest(group.encode())[:8],16)%100
    return 'train' if n<70 else ('validation' if n<85 else 'test')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--observations-per-species',type=int,default=12)
    ap.add_argument('--max-media-mib',type=int,default=512)
    ap.add_argument('--image-size',choices=['medium','large'],default='medium')
    ap.add_argument('--resume',action='store_true',help='Reuse completed species from the same collection configuration')
    args=ap.parse_args()
    if not 1 <= args.observations_per_species <= 200:ap.error("observations-per-species must be 1..200")
    out=args.output;out.mkdir(parents=True,exist_ok=True)
    rows=list(csv.DictReader((ROOT/'data/priority-species.tsv').open(),delimiter='\t'))
    cached=out/'ukraine-checklist.zip'
    if not cached.exists(): cached.write_bytes(get('https://ukraine.ipt.gbif.no/archive.do?r=test'))
    z=zipfile.ZipFile(cached); raw=list(csv.DictReader(io.StringIO(z.read('taxon.txt').decode()),delimiter='\t'))
    occurrences=list(csv.DictReader(io.StringIO(z.read('occurrence.txt').decode()),delimiter='\t'))
    evidence=defaultdict(Counter)
    for o in occurrences: evidence[o['taxonID']][o.get('stateProvince') or 'unknown']+=1
    taxa={}; cards={}; mappings={}; source_report=[]; stats=[]; images=[]; budget=0
    for r in raw:
        name=r['scientificName']; id='reference:'+name.lower().replace(' ','-')
        taxa[name]={'id':id,'parentID':None,'scientificName':name,'rank':r['taxonRank'],
          'names':{},'synonyms':[],'support':'referenceOnly','category':'unknown_or_disputed',
          'sourceURL':'https://www.gbif.org/dataset/f994f6e8-4d7d-45bd-ab10-d59ecdfdbe80',
          'taxonomyVersion':'0.1.2-source-snapshot'}
        cards[id]={'taxonID':id,'traits':{'uk':[],'en':[]},'reviewStatus':'no_species_traits',
          'regions':dict(evidence[r['taxonID']]),'ukraineEvidence':'published_checklist',
          'sourceURL':taxa[name]['sourceURL'],'sourceTaxonIDs':[r['taxonID']],
          'missing':['morphology_review','expert_approval','multi_view_photos'],'photos':[]}
    dataset=out/'TrainingData';(dataset/'images').mkdir(parents=True,exist_ok=True)
    old_stats={};old_images=[]
    if args.resume and (out/'priority-data-gaps.json').exists() and (dataset/'manifest.jsonl').exists():
        old_stats={v['name']:v for v in json.loads((out/'priority-data-gaps.json').read_text())}
        old_images=[json.loads(line) for line in (dataset/'manifest.jsonl').read_text().splitlines()]
        budget=sum(r['size_bytes'] for r in old_images)

    for i,r in enumerate(rows):
        name=r['scientificName'];id='reference:'+name.lower().replace(' ','-')
        t=taxa.setdefault(name,{'id':id,'parentID':None,'scientificName':name,'rank':'species','names':{},'synonyms':[],
            'support':'referenceOnly','category':'unknown_or_disputed','sourceURL':'https://www.gbif.org/species/search?q='+urllib.parse.quote(name),'taxonomyVersion':'0.1.2-source-snapshot'})
        t['names']={'uk':r['uk'],'en':r['en']}
        if name in ALIASES:t['synonyms']=[ALIASES[name]]
        page=({'Xerocomus subtomentosus':'Boletus subtomentosus','Hypholoma lateritium':'Hypholoma lateritium','Inosperma erubescens':'Inocybe erubescens'}.get(name,ALIASES.get(name,name))).lower().replace(' ','-')
        url='https://www.first-nature.com/fungi/'+page+'.php'
        status='source_unavailable';source_hash=None
        try:
            b=get(url);source_hash=digest(b);status='editorial_draft_source_retrieved'
        except Exception as e: source_report.append({'name':name,'error':type(e).__name__})
        previous=cards.get(id,{})
        cards[id]={'taxonID':id,'traits':{'uk':r['ukFacts'].split(';'),'en':r['enFacts'].split(';')},
          'reviewStatus':status,'regions':previous.get('regions',{}),
          'ukraineEvidence':previous.get('ukraineEvidence','unconfirmed_for_this_species'),
          'sourceURL':url,'sourceSHA256':source_hash,'sourceTaxonIDs':previous.get('sourceTaxonIDs',[]),
          'missing':['expert_approval','multi_view_photos','lighting_labels','field_validation'],
          'photos':[],'priorityGroup':r['group']}
        mappings[id]={'name':name,'group':r['group']}
        print(f'{i+1}/{len(rows)} {name}',flush=True)
        if name in old_stats and old_stats[name]["photos"] > 0:
            reused=[v for v in old_images if v['scientific_name']==name]
            images.extend(reused);stats.append(old_stats[name]);cards[id]['photos']=reused[:3]
            if any(v['country']=='UA' for v in reused):cards[id]['ukraineEvidence']='community_record_or_checklist'
            continue
        observations=[];inat=None;ua_count=0
        try:
            lookup=api('https://api.inaturalist.org/v1/taxa/autocomplete',{'q':name,'per_page':10})
            inat=next((v for v in lookup['results'] if v['name']==name and v.get('rank')=='species'),None)
            if not inat and name in ALIASES:
                lookup=api('https://api.inaturalist.org/v1/taxa/autocomplete',{'q':ALIASES[name],'per_page':10})
                inat=next((v for v in lookup['results'] if v['name']==ALIASES[name] and v.get('rank')=='species'),None)
            if inat:
                base={'taxon_id':inat['id'],'quality_grade':'research','license':'cc0,cc-by','photo_license':'cc0,cc-by',
                    'photos':'true','captive':'false','per_page':args.observations_per_species,'order_by':'id','order':'desc'}
                ua=api('https://api.inaturalist.org/v1/observations',{**base,'place_id':8860})
                ua_count=ua['total_results'];observations=[(o,'UA') for o in ua['results']]
                if len(observations)<args.observations_per_species:
                    other=api('https://api.inaturalist.org/v1/observations',base)
                    seen={o['id'] for o,_ in observations}
                    observations += [(o,None) for o in other['results'] if o['id'] not in seen]
            else: source_report.append({'name':name,'error':'no_exact_inaturalist_species_match'})
        except Exception as e:
            print('API error',name,type(e).__name__,flush=True)
            source_report.append({'name':name,'error':type(e).__name__})
        candidates=[]
        for o,country in observations[:args.observations_per_species]:
            if o.get('license_code') not in LICENSES or o.get('taxon',{}).get('id') != (inat or {}).get('id'):continue
            if o.get('flags') or o.get('captive'):continue
            p=next((p for p in o.get('photos',[]) if p.get('license_code') in LICENSES),None)
            if not p:continue
            author=str(o['user']['id']);day=o.get('observed_on') or f"unknown-{o['id']}"
            # Split all observations from the same observer/day together, across species.
            group=author+':'+day
            record={'observation_id':o['id'],'photo_id':p['id'],'taxon_id':id,'inaturalist_taxon_id':inat['id'],
              'scientific_name':name,'label_basis':'community_research_grade','expert_verified':False,'bbox':None,
              'view':None,'lighting':None,'country':country,'observed_on':o.get('observed_on'),
              'observer_id':author,'session_group':group,'split':split(group),
              'observation_license':o['license_code'],'photo_license':p['license_code'],
              'attribution':p.get('attribution') or o['user'].get('login'),
              'source_url':f"https://www.inaturalist.org/observations/{o['id']}",
              'download_url':p['url'].replace('/square.',f'/{args.image_size}.'),'relative_path':f"images/{p['id']}.jpg"}
            candidates.append(record)
        async def download_all():
            semaphore=asyncio.Semaphore(8)
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                async def one(record):
                    async with semaphore:
                        p=dataset/record['relative_path']
                        try:
                            if not p.exists():
                                response=await asyncio.wait_for(client.get(record['download_url']), timeout=18)
                                response.raise_for_status();b=response.content
                                if len(b)>4*1024*1024 or not b.startswith(b'\xff\xd8'):return None
                                temp=p.with_suffix('.tmp');temp.write_bytes(b);temp.replace(p)
                            b=p.read_bytes()
                            if not b.startswith(b'\xff\xd8'):p.unlink(missing_ok=True);return None
                            record['sha256']=digest(b);record['size_bytes']=len(b);return record
                        except Exception as e:
                            return None
                return await asyncio.gather(*(one(record) for record in candidates))
        records=[]
        if budget<args.max_media_mib*1024**2:
            if HTTP is None:raise RuntimeError('Install httpx[socks] before collecting media')
            records=[v for v in asyncio.run(download_all()) if v is not None]
            budget+=sum(v['size_bytes'] for v in records)
        if len(records)<len(candidates):source_report.append({'name':name,'unfetched_photos':len(candidates)-len(records)})
        # Checkpoint each species so interrupted runs retain usable data and provenance.
        images.extend(records)
        (dataset/'manifest.jsonl').write_text(''.join(json.dumps(v,ensure_ascii=False)+'\n' for v in images))
        stats.append({'taxon_id':id,'name':name,'ukraine_licensed_observations_available':ua_count,'photos':len(records),
          'groups':len({v['session_group'] for v in records}),'ukraine_photos':sum(v['country']=='UA' for v in records)})
        if any(v['country']=='UA' for v in records):cards[id]['ukraineEvidence']='community_record_or_checklist'
        cards[id]['photos']=records[:3]
        write(out/'priority-data-gaps.json',stats)
        write(out/'source-report.json',source_report)
        print('saved',name,len(records),'UA available',ua_count,flush=True)
    # Same bytes crossing initial group splits must move together; retain conflicting labels for review.
    duplicates=defaultdict(list)
    for r in images:duplicates[r['sha256']].append(r)
    conflicts=[]
    for sha,group in duplicates.items():
        if len(group)>1:
            destination=split('sha:'+sha)
            for v in group:v['split']=destination
            if len({v['taxon_id'] for v in group})>1:conflicts.append({'sha256':sha,'observations':[v['observation_id'] for v in group]})
    # Enforce connected observer-day/duplicate components, not just pairwise moves.
    parent={r['session_group']:r['session_group'] for r in images}
    def find(x):
        while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
        return x
    for group in duplicates.values():
        for r in group[1:]:parent[find(r['session_group'])]=find(group[0]['session_group'])
    holdout_authors={r['observer_id'] for r in images if int(digest(('observer:'+r['observer_id']).encode())[:8],16)%13==0}
    holdout_groups={find(r['session_group']) for r in images if r['observer_id'] in holdout_authors}
    for r in images:
        r['split_group']=find(r['session_group'])
        r['split']='observer_holdout' if r['split_group'] in holdout_groups else split(r['split_group'])
    (dataset/'manifest.jsonl').write_text(''.join(json.dumps(v,ensure_ascii=False)+'\n' for v in images))
    write(dataset/'label-conflicts.json',conflicts)
    write(dataset/'report.json',{'photos':len(images),'bytes':budget,'species_with_photos':len({v['taxon_id'] for v in images}),
        'split_counts':dict(Counter(v['split'] for v in images)),'expert_verified':0,'bounding_boxes':0,
        'training_ready':False,'validation_needed':['expert_species_labels','perceptual_duplicate_review','negative_images','bounding_boxes','independent_field_holdout'],
        'source':'https://api.inaturalist.org/v1','license_allowlist':sorted(LICENSES)})
    write(out/'reference-cards.json',list(cards.values()))
    write(out/'taxonomy.json',sorted(taxa.values(),key=lambda t:t['scientificName']))
    write(out/'priority-groups.json',mappings)
    write(out/'source-report.json',source_report)
    write(out/'catalog-report.json',{'taxa':len(taxa),'checklist_rows':len(raw),'checklist_occurrences':len(occurrences),
      'individual_trait_cards':len(rows),'expert_reviewed_cards':0,'supported_model_classes':0,
      'checklist_archive_sha256':digest(cached.read_bytes()),'checklist_license':'CC0-1.0',
      'scope':'Agaricales published checklist plus explicit owner-priority species; not all fungi of Ukraine',
      'names':'checklist source names retained; synonym normalization incomplete',
      'traits':'original editorial paraphrases awaiting source and expert review; no copied source images or full descriptions'})
if __name__=='__main__':main()
