#!/usr/bin/env python3
"""Convert Label Studio RectangleLabels or PolygonLabels to YOLO datasets."""
from __future__ import annotations
import argparse,json,random,shutil
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs,unquote,urlparse
def n(t):
 raw=str((t.get('data')or{}).get('image',''));p=urlparse(raw);return Path(unquote(parse_qs(p.query).get('d',[raw])[0]).replace('\\','/')).name
def latest(a):return max(a,key=lambda x:str(x.get('updated_at')or x.get('created_at')or ''))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--image-root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--mode',choices=['detect','seg'],required=True);ap.add_argument('--train',type=float,default=.8);ap.add_argument('--val',type=float,default=.1);ap.add_argument('--seed',type=int,default=20261022);args=ap.parse_args()
 if args.output.exists() and any(args.output.iterdir()):raise FileExistsError(args.output)
 tasks=json.loads(args.input.read_text(encoding='utf-8-sig'));files={p.name:p for p in args.image_root.rglob('*') if p.is_file()}; raw=[]; classes=set(); skipped=[]; target='rectanglelabels' if args.mode=='detect' else 'polygonlabels'
 for t in tasks:
  if not t.get('annotations'):skipped.append({'task_id':t.get('id'),'reason':'no_annotation'});continue
  nn=n(t);src=files.get(nn)
  if not src:skipped.append({'task_id':t.get('id'),'image':nn,'reason':'image_missing'});continue
  items=[]
  for r in latest(t['annotations']).get('result',[]):
   v=r.get('value')or{}
   if r.get('type')!=target:continue
   labs=v.get(target)or[]
   if not labs:continue
   label=labs[0];classes.add(label)
   if args.mode=='detect':
    if min(float(v.get(k,-1)) for k in ('x','y','width','height'))<0:raise ValueError('invalid rectangle')
    items.append((label,[float(v[k])/100 for k in ('x','y','width','height')]))
   else:
    pts=v.get('points')or[]
    if len(pts)<3:continue
    items.append((label,[z/100 for pt in pts for z in pt]))
  raw.append((t.get('id'),nn,src,items))
 mapping={x:i for i,x in enumerate(sorted(classes))};rng=random.Random(args.seed);rng.shuffle(raw);a=round(len(raw)*args.train);b=round(len(raw)*args.val);splits={'train':raw[:a],'val':raw[a:a+b],'test':raw[a+b:]}
 for split,rows in splits.items():
  im=args.output/'images'/split;lb=args.output/'labels'/split;im.mkdir(parents=True,exist_ok=True);lb.mkdir(parents=True,exist_ok=True)
  for tid,nn,src,items in rows:
   shutil.copy2(src,im/nn)
   lines=[]
   for label,data in items:
    if args.mode=='detect': x,y,w,h=data;data=[x+w/2,y+h/2,w,h]
    lines.append(str(mapping[label])+' '+' '.join(f'{z:.6f}' for z in data))
   (lb/f'{Path(nn).stem}.txt').write_text('\n'.join(lines)+('\n' if lines else ''),encoding='utf8')
 (args.output/'data.yaml').write_text('path: .\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n'+''.join(f'  {v}: {k}\n'for k,v in mapping.items()),encoding='utf8')
 report={'mode':args.mode,'classes':mapping,'counts':{k:len(v)for k,v in splits.items()},'empty_label_images':sum(not x[3]for x in raw),'skipped':skipped};(args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
