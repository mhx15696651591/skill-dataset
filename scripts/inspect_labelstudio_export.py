#!/usr/bin/env python3
"""Summarize Label Studio annotation structure without altering the export."""
from __future__ import annotations
import argparse, json
from collections import Counter
from pathlib import Path

def values(result: dict) -> list[str]:
    value = result.get("value") or {}
    for key in ("choices", "brushlabels", "polygonlabels", "rectanglelabels", "keypointlabels"):
        if value.get(key): return [str(x) for x in value[key]]
    return []

def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("input", type=Path); args=ap.parse_args()
    tasks=json.loads(args.input.read_text(encoding="utf-8-sig"))
    results=[r for t in tasks for a in t.get("annotations",[]) for r in a.get("result",[])]
    report={"input":str(args.input),"tasks":len(tasks),"annotated_tasks":sum(bool(t.get("annotations")) for t in tasks),
      "annotation_count":sum(len(t.get("annotations",[])) for t in tasks),
      "result_types":dict(Counter(str(r.get("type")) for r in results)),
      "controls":dict(Counter(str(r.get("from_name")) for r in results)),
      "labels":dict(Counter(x for r in results for x in values(r))),
      "duplicate_annotation_tasks":sum(len(t.get("annotations",[]))>1 for t in tasks),
      "image_examples":[str((t.get("data") or {}).get("image","")) for t in tasks[:3]]}
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
