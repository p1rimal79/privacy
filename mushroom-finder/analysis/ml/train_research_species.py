"""Community-label RESEARCH experiment. Does not alter production training eligibility.
No food-safety conclusion, expert verification or field acceptance is created here.
"""
import argparse, copy, hashlib, json, random, time
from pathlib import Path
from collections import Counter
import numpy as np
import torch, timm
from PIL import Image
from safetensors.torch import load_file
from torchvision import transforms

def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--known',type=Path,required=True);ap.add_argument('--unknown',type=Path,required=True);ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--finetune-epochs',type=int,default=4);a=ap.parse_args()
    torch.set_num_threads(8);torch.manual_seed(20261014);np.random.seed(20261014);random.seed(20261014)
    a.output.mkdir(parents=True,exist_ok=True)
    records=[]
    for path in [a.known,a.unknown]:
        for r in map(json.loads,path.read_text().splitlines()):
            p=path.parent/r['relative_path'];assert sha(p)==r['sha256']
            assert r['photo_license'] in {'cc0','cc-by'} and r['observation_license'] in {'cc0','cc-by'}
            records.append({**r,'path':str(p)})
    # All duplicate bytes and observer/day groups share a split; holdout observers never enter training.
    by_group={};by_sha={}
    for r in records:
        assert by_group.setdefault(r['session_group'],r['split'])==r['split'],'session_split_conflict'
        assert by_sha.setdefault(r['sha256'],r['split'])==r['split'],'image_split_conflict'
    held={r['observer_id'] for r in records if r['split']=='observer_holdout'}
    assert not held & {r['observer_id'] for r in records if r['split']!='observer_holdout'}
    counts=Counter((r['taxon_id'],r['split']) for r in records if r['taxon_id']!='unknown')
    classes=sorted({r['taxon_id'] for r in records if r['taxon_id']!='unknown' and counts[r['taxon_id'],'train']>=20 and counts[r['taxon_id'],'validation']>=4})
    unknown=len(classes);ids={tid:i for i,tid in enumerate(classes)}
    unique={}
    for r in records:
        r['label']=ids.get(r['taxon_id'],unknown);unique.setdefault(r['sha256'],r)
    records=list(unique.values())
    dump(a.output/'class-index.json',{'classes':classes,'unknown_index':unknown,'expert_verified':False})
    dump(a.output/'experiment-samples.json',[{k:r[k] for k in ['photo_id','sha256','taxon_id','label','split','session_group','observer_id']} for r in records])
    model=timm.create_model('efficientnet_b0',pretrained=False,num_classes=0)
    state=load_file(str(a.source/'model.safetensors'));state={k:v for k,v in state.items() if not k.startswith('classifier.')}
    model.load_state_dict(state,strict=True);model.eval()
    prep=transforms.Compose([transforms.Resize((224,224)),transforms.ToTensor(),transforms.Normalize([.485,.456,.406],[.229,.224,.225])])
    class Images(torch.utils.data.Dataset):
        def __init__(self,rows,augment=False):self.rows=rows;self.augment=augment
        def __len__(self):return len(self.rows)
        def __getitem__(self,i):
            r=self.rows[i]
            with Image.open(r['path']) as im:
                im=im.convert('RGB')
                if self.augment and random.random()<.5:im=im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                return prep(im),r['label']
    rows_by_split={s:[r for r in records if r['split']==s] for s in ['train','validation','test','observer_holdout']}
    features={}
    with torch.no_grad():
        for split,rows in rows_by_split.items():
            chunks=[];labels=[]
            for n,(x,y) in enumerate(torch.utils.data.DataLoader(Images(rows),batch_size=32,num_workers=0)):
                chunks.append(model(x));labels.append(y)
                if n%10==0:print('features',split,n,len(rows),flush=True)
            features[split]=(torch.cat(chunks),torch.cat(labels))
    torch.save(features,a.output/'feature-cache.pt')
    head=torch.nn.Linear(model.num_features,unknown+1)
    optimizer=torch.optim.AdamW(head.parameters(),lr=.008,weight_decay=.02)
    xf,yf=features['train'];vx,vy=features['validation'];best=float('inf');best_head=None
    for epoch in range(160):
        head.train()
        for indexes in torch.randperm(len(yf)).split(128):
            loss=torch.nn.functional.cross_entropy(head(xf[indexes]),yf[indexes]);optimizer.zero_grad();loss.backward();optimizer.step()
        head.eval()
        with torch.no_grad():val=torch.nn.functional.cross_entropy(head(vx),vy).item()
        if val<best:best=val;best_head=copy.deepcopy(head.state_dict())
    head.load_state_dict(best_head);print('linear validation CE',best,flush=True)
    class Network(torch.nn.Module):
        def __init__(self,backbone,head):super().__init__();self.backbone=backbone;self.head=head
        def forward(self,x):return self.head(self.backbone(x))
    net=Network(model,head);best_state=copy.deepcopy(net.state_dict());history=[{'stage':'linear','validation_ce':best}]
    for p in model.parameters():p.requires_grad=False
    for module in [model.blocks[-1],model.conv_head,model.bn2]:
        for p in module.parameters():p.requires_grad=True
    optimizer=torch.optim.AdamW([p for p in net.parameters() if p.requires_grad],lr=.0002,weight_decay=.01)
    train_loader=torch.utils.data.DataLoader(Images(rows_by_split['train'],True),batch_size=24,shuffle=True,num_workers=0)
    val_loader=torch.utils.data.DataLoader(Images(rows_by_split['validation']),batch_size=32,num_workers=0)
    def logits(loader):
        net.eval();result=[]
        with torch.no_grad():
            for x,y in loader:result.append(net(x))
        return torch.cat(result)
    for epoch in range(a.finetune_epochs):
        net.train();model.eval() # Keep batch-normalization statistics frozen with small provisional classes.
        for batch,(x,y) in enumerate(train_loader):
            loss=torch.nn.functional.cross_entropy(net(x),y);optimizer.zero_grad();loss.backward();optimizer.step()
            if batch%20==0:print('finetune',epoch+1,batch,float(loss.detach()),flush=True)
        vl=logits(val_loader);ce=torch.nn.functional.cross_entropy(vl,vy).item()
        history.append({'stage':'finetune','epoch':epoch+1,'validation_ce':ce});print(history[-1],flush=True)
        if ce<best:best=ce;best_state=copy.deepcopy(net.state_dict())
    net.load_state_dict(best_state);net.eval();vl=logits(val_loader)
    # Fit temperature and rejection only on validation. Test/observer holdout are evaluated afterwards.
    log_temperature=torch.nn.Parameter(torch.zeros(()));opt=torch.optim.LBFGS([log_temperature],lr=.1,max_iter=60)
    def closure():
        opt.zero_grad();loss=torch.nn.functional.cross_entropy(vl/log_temperature.exp().clamp(.25,8),vy);loss.backward();return loss
    opt.step(closure);temperature=float(log_temperature.exp().clamp(.25,8).detach())
    probabilities=(vl/temperature).softmax(-1);maximum,pred=probabilities.max(-1)
    sorted_scores=probabilities.topk(2,dim=-1).values;margin=sorted_scores[:,0]-sorted_scores[:,1]
    candidates=[]
    for threshold in np.arange(.2,.96,.025):
        for gap in [.05,.1,.15,.2]:
            mask=(pred!=unknown)&(maximum>=float(threshold))&(margin>=gap)
            count=int(mask.sum());precision=float((pred[mask]==vy[mask]).float().mean()) if count else 0
            if count>=10 and precision>=.8:candidates.append((count,precision,float(threshold),gap))
    gate=max(candidates) if candidates else (0,0,1.0,1.0)
    metrics={};predictions=[]
    for split,rows in rows_by_split.items():
        dl=torch.utils.data.DataLoader(Images(rows),batch_size=32,num_workers=0);p=(logits(dl)/temperature).softmax(-1);y=torch.tensor([r['label'] for r in rows]);score,pr=p.max(-1);top=p.topk(min(3,p.shape[1]),dim=-1).indices
        margins=p.topk(2,dim=-1).values;mask=(pr!=unknown)&(score>=gate[2])&((margins[:,0]-margins[:,1])>=gate[3]);unknown_mask=y==unknown
        metrics[split]={'images':len(rows),'top1_vs_community_labels':float((pr==y).float().mean()),'top3_vs_community_labels':float((top==y[:,None]).any(-1).float().mean()),'unknown_images':int(unknown_mask.sum()),'unknown_abstention_rate':float((~mask[unknown_mask]).float().mean()) if unknown_mask.any() else None,'shortlisted':int(mask.sum()),'shortlist_precision_vs_community_labels':float((pr[mask]==y[mask]).float().mean()) if mask.any() else None,'per_class':{classes[i] if i<unknown else 'unknown':{'count':int((y==i).sum()),'top1':float((pr[y==i]==i).float().mean()) if (y==i).any() else None} for i in range(unknown+1)}}
        for r,prob,guess,accepted in zip(rows,p.tolist(),pr.tolist(),mask.tolist()):predictions.append({'photo_id':r['photo_id'],'split':split,'source_label':r['taxon_id'],'prediction':classes[guess] if guess<unknown else 'unknown','shortlisted':accepted,'scores':prob})
    dump(a.output/'predictions.json',predictions)
    card={'status':'engineering_candidate','expert_verified':False,'supported_production_taxa':[],'source_label_quality':'community only, not expert biological truth','backbone':json.loads((a.source/'provenance.json').read_text()),'dataset_hashes':{'known':sha(a.known),'unknown':sha(a.unknown)},'classes':classes,'unknown_index':unknown,'temperature':temperature,'shortlist_threshold':gate[2],'minimum_margin':gate[3],'validation_gate_found':bool(candidates),'metrics':metrics,'training_history':history,'limitations':['small unreviewed classes','uncertified source unknowns','whole-photo vs crop domain shift','some photos contain multiple specimens','no independent forest event test','no edibility finding','Core ML runtime not tested on Linux']}
    dump(a.output/'species-model-card.json',card)
    torch.save({'state_dict':net.state_dict(),'classes':classes,'temperature':temperature,'status':'research_community_labels'},a.output/'species-research.pt')
    class Export(torch.nn.Module):
        def __init__(self):
            super().__init__();self.net=net;self.register_buffer('mean',torch.tensor([.485,.456,.406]).reshape(1,3,1,1));self.register_buffer('std',torch.tensor([.229,.224,.225]).reshape(1,3,1,1))
        def forward(self,image):return (self.net((image-self.mean)/self.std)/temperature).softmax(-1)
    export=Export().eval();x=torch.rand(1,3,224,224);traced=torch.jit.trace(export,x)
    parity=float((export(x)-traced(x)).abs().max().detach());assert parity<1e-5
    import coremltools as ct
    package=ct.convert(traced,inputs=[ct.ImageType(name='image',shape=x.shape,scale=1/255,color_layout=ct.colorlayout.RGB)],outputs=[ct.TensorType(name='class_scores')],minimum_deployment_target=ct.target.iOS16,convert_to='mlprogram')
    package.short_description='Experimental mushroom shortlist; community labels; not an edibility assessment.'
    package.save(str(a.output/'MushroomSpecies.mlpackage'))
    dump(a.output/'export-report.json',{'torch_trace_max_error':parity,'coreml_runtime':'blocked_linux','input':'RGB 224x224 stretch; scale 1/255; model applies mean/std','output':'class_scores [1, known_classes+1]','package_hashes':{str(p.relative_to(a.output/'MushroomSpecies.mlpackage')):sha(p) for p in (a.output/'MushroomSpecies.mlpackage').rglob('*') if p.is_file()}})
    print(json.dumps(metrics,indent=2),flush=True)
if __name__=='__main__':main()
