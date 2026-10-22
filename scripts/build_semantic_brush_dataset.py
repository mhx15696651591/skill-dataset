#!/usr/bin/env python3
"""Convert Label Studio BrushLabels RLE into a split semantic-segmentation set."""
from __future__ import annotations
import argparse, json, random, shutil
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
import cv2, numpy as np

def image_name(task):
    raw=str((task.get("data") or {}).get("image", "")); p=urlparse(raw)
    return Path(unquote(parse_qs(p.query).get("d",[raw])[0]).replace("\\","/")).name

class Bits:
    def __init__(self,x): self.x=[int(a)&255 for a in x]; self.i=0
    def read(self,n):
        if self.i+n>8*len(self.x): raise ValueError("truncated compressed RLE")
        v=0
        for _ in range(n): v=(v<<1)|((self.x[self.i//8]>>(7-self.i%8))&1); self.i+=1
        return v
def decode(rle,h,w):
    b=Bits(rle); n=b.read(32); word=b.read(5)+1; sizes=[b.read(4)+1 for _ in range(4)]
    if n != h*w*4: raise ValueError(f"RLE shape mismatch: {n} != {h}*{w}*4")
    out=np.zeros(n,np.uint8); i=0
    while i<n:
        repeat=b.read(1); end=i+1+b.read(sizes[b.read(2)])
        if end>n: raise ValueError("invalid RLE run")
        if repeat: out[i:end]=b.read(word); i=end
        else:
            while i<end: out[i]=b.read(word); i+=1
    return out.reshape(h,w,4)[:,:,3]>0
def latest(items):
    return max(items,key=lambda a:str(a.get("updated_at") or a.get("created_at") or ""))
def write(path,arr):
    ok,b=cv2.imencode(path.suffix,arr)
    if not ok: raise RuntimeError(f"cannot encode {path}")
    b.tofile(str(path))
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,required=True); ap.add_argument("--image-root",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True); ap.add_argument("--class",dest="classes",action="append",required=True,help="LABEL=MASK_VALUE, repeatable")
    ap.add_argument("--train",type=float,default=.8); ap.add_argument("--val",type=float,default=.1); ap.add_argument("--seed",type=int,default=20261022); ap.add_argument("--overwrite",action="store_true")
    args=ap.parse_args(); mapping={}
    for text in args.classes:
        label,value=text.rsplit("=",1); mapping[label]=int(value)
    if 0 in mapping.values() or len(set(mapping.values()))!=len(mapping): raise ValueError("class values must be unique non-zero integers")
    if args.output.exists() and any(args.output.iterdir()) and not args.overwrite: raise FileExistsError(f"output exists: {args.output}")
    tasks=json.loads(args.input.read_text(encoding="utf-8-sig")); lookup={p.name:p for p in args.image_root.rglob("*") if p.is_file()}
    records=[]; skipped=[]
    for task in tasks:
        anns=task.get("annotations") or []
        if not anns: skipped.append({"task_id":task.get("id"),"reason":"no_annotation"}); continue
        ann=latest(anns); name=image_name(task); source=lookup.get(name)
        if not source: skipped.append({"task_id":task.get("id"),"image":name,"reason":"image_missing"}); continue
        img=cv2.imdecode(np.fromfile(str(source),np.uint8),cv2.IMREAD_COLOR)
        if img is None: skipped.append({"task_id":task.get("id"),"image":name,"reason":"image_unreadable"}); continue
        mask=np.zeros(img.shape[:2],np.uint8); failed=None
        for r in ann.get("result",[]):
            v=r.get("value") or {}; labels=v.get("brushlabels") or []
            if r.get("type")!="brushlabels" or not labels or not v.get("rle"): continue
            unknown=set(labels)-set(mapping)
            if unknown: failed=f"unknown_class:{','.join(sorted(unknown))}"; break
            try: fg=decode(v["rle"],int(r["original_height"]),int(r["original_width"]))
            except Exception as e: failed=f"rle_decode:{e}"; break
            if fg.shape!=mask.shape: failed="image_annotation_size_mismatch"; break
            value=mapping[labels[0]]
            if np.any((mask>0)&fg&(mask!=value)): failed="class_overlap"; break
            mask[fg]=value
        if failed: skipped.append({"task_id":task.get("id"),"image":name,"reason":failed}); continue
        if not mask.any(): skipped.append({"task_id":task.get("id"),"image":name,"reason":"empty_mask"}); continue
        records.append((task.get("id"),name,source,img,mask))
    rng=random.Random(args.seed); rng.shuffle(records); n=len(records); a=round(n*args.train); b=round(n*args.val); groups={"train":records[:a],"val":records[a:a+b],"test":records[a+b:]}
    manifest={};
    for split,rows in groups.items():
        (args.output/"images"/split).mkdir(parents=True,exist_ok=True); (args.output/"masks"/split).mkdir(parents=True,exist_ok=True); manifest[split]=[]
        for tid,name,source,img,mask in rows:
            dst=args.output/"images"/split/name; shutil.copy2(source,dst); mp=args.output/"masks"/split/f"{Path(name).stem}.png"; write(mp,mask)
            manifest[split].append({"task_id":tid,"image":f"images/{split}/{name}","mask":f"masks/{split}/{mp.name}"})
    report={"input":str(args.input),"classes":mapping,"seed":args.seed,"counts":{k:len(v) for k,v in manifest.items()},"skipped":skipped,"valid":len(records)}
    (args.output/"dataset.yaml").write_text("task: semantic_segmentation\nclasses:\n"+"".join(f"  {v}: {k}\n" for k,v in mapping.items()),encoding="utf8")
    (args.output/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf8"); (args.output/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
