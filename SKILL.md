---
name: vision-dataset-builder
description: Build reproducible computer-vision datasets from Label Studio JSON exports. Use for classification, object detection, instance segmentation, or semantic segmentation dataset conversion, validation, and train/val/test splitting; do not use for label-statistics-only requests.
---

# Visual Dataset Builder

Use this skill to turn a Label Studio export and local source images into a
versioned, ready-to-train visual dataset. It orchestrates deterministic scripts;
the scripts, rather than this skill, perform the potentially large image and
annotation conversion work.

## First: inspect, then route

Run `scripts/inspect_labelstudio_export.py` before creating any dataset. Report
the task count, annotation types, controls, labels, duplicate annotations,
unannotated tasks, and image-reference pattern.

Select a route from the actual annotation structure:

| Label Studio result type | Route | Typical output |
|---|---|---|
| `choices` only | classification | image folders plus CSV/JSON labels |
| `rectanglelabels` | detection | YOLO-Detect TXT or COCO |
| `polygonlabels` | instance segmentation by default | YOLO-Seg TXT or COCO segmentation |
| `brushlabels` with one merged foreground/class map per image | semantic segmentation | single-channel PNG class masks |
| `brushlabels` that must preserve each separate object | instance segmentation | ask whether to emit YOLO-Seg or COCO |
| multiple types | mixed task | report the branches and ask which output(s) to build |

If the user explicitly names the training format, follow it. If a brush or
polygon export could reasonably mean semantic or instance segmentation, ask one
short question: whether independently drawn regions must remain separate. Do
not guess the image root, output root, class meanings, or an overwrite target.

## Semantic BrushLabels route

For a foreground/background or multi-class pixel segmentation project, use
`scripts/build_semantic_brush_dataset.py`. It supports native compressed Label
Studio BrushLabels RLE and combines all same-class brush annotations in a task.

Required inputs:

- Label Studio JSON export;
- source image root (recursive filename lookup is available for nested folders);
- output directory that is new or explicitly approved for replacement;
- class mapping, in the desired mask values; and
- split ratios and random seed (default `0.8/0.1/0.1`, `20261022`).

The output contains:

```text
output/
  images/{train,val,test}/
  masks/{train,val,test}/       # single-channel PNG: 0=background
  dataset.yaml                  # task, class mapping, split paths
  manifest.json                 # every copied image/mask and source task
  report.json                   # counts, skipped records, validation status
```

When a task has several final annotations, preserve only the latest one for the
same selected annotator. If several annotators are intentionally selected,
require a declared final-label policy; do not silently blend their masks.

For multi-class masks, verify that a pixel cannot silently receive two class
values. Stop and report overlap unless the user has provided class priority.

## Universal validation

Before reporting completion, verify:

1. every split image has an expected annotation file/mask;
2. image and mask dimensions match for semantic segmentation;
3. no source image appears in more than one split;
4. labels/masks contain only the declared class values;
5. the report distinguishes valid output, missing source images, missing labels,
   empty masks, and decode failures.

Never overwrite source JSON or source images. Write a date/versioned output
directory. Keep rejected or incomplete records in `report.json` so they can be
reviewed rather than disappearing from sample counts.

## Other routes

The detection, instance-segmentation, and classification converter scripts are
not yet part of this first semantic-segmentation release. When the inspection
selects one of those routes, explain the detected structure and either add the
appropriate converter to this skill or use a project-specific existing
converter; do not force it through semantic-mask conversion.
