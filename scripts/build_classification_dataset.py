#!/usr/bin/env python3
"""Build a single- or multi-label classification dataset from Label Studio Choices."""
from __future__ import annotations
import argparse, csv, json, random, shutil
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

def name(task):
 raw=str((task.get('data')or{}).get('image','')); p=urlparse(raw); return Path(unquote(parse_qs(p.query).get('d',[raw])[0]).replace('\\','/')).name
def latest(anns): return max(anns,key=lambda a:str(a.get('updated_at')or a.get('created_at')or ''))
def choices(a, field): return [str(x) for r in a.get('result',[]) if r.get('from_name')==field for x in (r.get('value')or{}).get('choices',[])]
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,required=True); ap.add_argument('--image-root',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); ap.add_argument('--field',required=True); ap.add_argument('--annotator',action='append'); ap.add_argument('--qa-field'); ap.add_argument('--qa-value',default='QA_PASS'); ap.add_argument('--train',type=float,default=.8); ap.add_argument('--val',type=float,default=.1); ap.add_argument('--seed',type=int,default=20261022); args=ap.parse_args()
 if args.output.exists() and any(args.output.iterdir()): raise FileExistsError(args.output)
 tasks=json.loads(args.input.read_text(encoding='utf-8-sig')); files={p.name:p for p in args.image_root.rglob('*') if p.is_file()}; rows=[]; skipped=[]
 for t in tasks:
  anns=[a for a in t.get('annotations',[]) if not args.annotator or str(a.get('completed_by')) in args.annotator]
  if not anns: skipped.append({'task_id':t.get('id'),'reason':'no_selected_annotation'}); continue
  a=latest(anns); labels=choices(a,args.field)
  if args.qa_field and args.qa_value not in choices(a,args.qa_field): skipped.append({'task_id':t.get('id'),'reason':'qa_filtered'}); continue
  if not labels: skipped.append({'task_id':t.get('id'),'reason':'empty_class_label'}); continue
  n=name(t); source=files.get(n)
  if not source: skipped.append({'task_id':t.get('id'),'image':n,'reason':'image_missing'}); continue
  rows.append({'task_id':t.get('id'),'image_name':n,'labels':sorted(set(labels))})
 rng=random.Random(args.seed); rng.shuffle(rows); a=round(len(rows)*args.train); b=round(len(rows)*args.val); splits={'train':rows[:a],'val':rows[a:a+b],'test':rows[a+b:]}
 for split,items in splits.items():
  folder=args.output/'images'/split; folder.mkdir(parents=True,exist_ok=True)
  with (args.output/f'{split}.csv').open('w',newline='',encoding='utf8') as f:
   w=csv.DictWriter(f,fieldnames=['task_id','image','labels']); w.writeheader()
   for r in items: shutil.copy2(files[r['image_name']],folder/r['image_name']); w.writerow({'task_id':r['task_id'],'image':f'images/{split}/{r["image_name"]}','labels':'|'.join(r['labels'])})
 counts=Counter(x for r in rows for x in r['labels']); report={'field':args.field,'valid':len(rows),'counts':{k:len(v) for k,v in splits.items()},'label_counts':dict(counts),'skipped':skipped,'seed':args.seed}
 (args.output/'class_mapping.json').write_text(json.dumps({x:i for i,x in enumerate(sorted(counts))},ensure_ascii=False,indent=2),encoding='utf8'); (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8'); print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
