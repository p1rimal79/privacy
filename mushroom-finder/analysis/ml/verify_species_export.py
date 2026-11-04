"""Verify real-photo tracing and emit a Mac Core ML parity runner and attributed golden inputs."""
import argparse,json,hashlib,shutil
from pathlib import Path
import torch,timm,numpy as np
from PIL import Image

def main():
    p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True);p.add_argument('--known',type=Path,required=True);p.add_argument('--unknown',type=Path,required=True);a=p.parse_args()
    torch.set_num_threads(8);checkpoint=torch.load(a.model/'species-research.pt',map_location='cpu',weights_only=True)
    class Network(torch.nn.Module):
        def __init__(self):super().__init__();self.backbone=timm.create_model('efficientnet_b0',num_classes=0,pretrained=False);self.head=torch.nn.Linear(self.backbone.num_features,len(checkpoint['classes'])+1)
        def forward(self,x):return self.head(self.backbone(x))
    net=Network();net.load_state_dict(checkpoint['state_dict']);net.eval()
    class Export(torch.nn.Module):
        def __init__(self):super().__init__();self.net=net;self.register_buffer('mean',torch.tensor([.485,.456,.406]).reshape(1,3,1,1));self.register_buffer('std',torch.tensor([.229,.224,.225]).reshape(1,3,1,1))
        def forward(self,x):return (self.net((x-self.mean)/self.std)/checkpoint['temperature']).softmax(-1)
    wrapper=Export().eval();traced=torch.jit.trace(wrapper,torch.zeros(1,3,224,224));golden=a.model/'Golden';golden.mkdir(exist_ok=True);(golden/'images').mkdir(exist_ok=True)
    cases=[];worst=0.
    for manifest in [a.known,a.unknown]:
        rows=[r for r in map(json.loads,manifest.read_text().splitlines()) if r['split']=='test'][:12]
        for row in rows:
            path=manifest.parent/row['relative_path'];name=str(row['photo_id'])+'.jpg';shutil.copy2(path,golden/'images'/name)
            with Image.open(path) as image:
                values=np.array(image.convert('RGB').resize((224,224),Image.Resampling.BILINEAR)).copy()
            x=torch.from_numpy(values).permute(2,0,1).unsqueeze(0).float()/255
            with torch.no_grad():e=wrapper(x);q=traced(x)
            error=float((e-q).abs().max());worst=max(worst,error)
            cases.append({'filename':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'scores':q[0].tolist(),'attribution':row['attribution'],'license':row['photo_license'],'source_url':row['source_url']})
    assert worst<1e-5
    (golden/'cases.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2)+'\n')
    (a.model/'real-photo-parity.json').write_text(json.dumps({'images':len(cases),'torch_trace_max_error':worst,'native_coreml':'blocked_no_macos','pixelbuffer_orientation':'blocked_no_iphone'},indent=2)+'\n')
    print('Real-photo trace parity',len(cases),worst)
if __name__=='__main__':main()
