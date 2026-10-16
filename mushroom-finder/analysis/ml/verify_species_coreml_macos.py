"""Run on macOS against a model experiment directory. Fails if numerical parity is poor."""
import argparse,json,platform
from pathlib import Path
import numpy as np
from PIL import Image
def main():
    p=argparse.ArgumentParser();p.add_argument('model',type=Path);a=p.parse_args()
    if platform.system()!='Darwin':raise SystemExit('blocked_no_macos_coreml_runtime')
    import coremltools as ct
    model=ct.models.MLModel(str(a.model/'MushroomSpecies.mlpackage'),compute_units=ct.ComputeUnit.CPU_ONLY)
    errors=[];top_agreements=[]
    for case in json.loads((a.model/'Golden/cases.json').read_text()):
        with Image.open(a.model/'Golden/images'/case['filename']) as image:image=image.convert('RGB').resize((224,224),Image.Resampling.BILINEAR)
        scores=np.asarray(model.predict({'image':image})['class_scores']).reshape(-1);expected=np.array(case['scores'])
        assert scores.shape==expected.shape and np.isfinite(scores).all()
        errors.append(float(np.max(np.abs(scores-expected))));top_agreements.append(int(scores.argmax()==expected.argmax()))
    report={'images':len(errors),'maximum_error':max(errors),'top1_agreement':sum(top_agreements)/len(errors),'cpu_coreml_runtime':'executed'}
    (a.model/'macos-parity-report.json').write_text(json.dumps(report,indent=2)+'\n')
    assert max(errors)<.01 and all(top_agreements),report
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
