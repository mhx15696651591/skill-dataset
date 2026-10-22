# Vision Dataset Builder

从 Label Studio 导出的 JSON 制作可复现的计算机视觉训练数据集。

当前版本支持四条常用链路：分类、YOLO 目标检测、YOLO 实例分割、BrushLabels 语义分割；均可复制原图并按指定随机种子划分 `train / val / test`。

## 适用场景

- 二值语义分割，例如 `背景 / 头发`、`背景 / 病灶`；
- 多类别语义分割，例如不同组织或病灶类别使用不同像素值；
- Label Studio 使用 `BrushLabels` 标注，且同类笔刷区域应合并为同一类别 mask。

同时支持：

- `Choices`：单标签或多标签分类，输出分割后的图片与 CSV 标签；
- `RectangleLabels`：YOLO Detect；
- `PolygonLabels`：YOLO-Seg 实例分割。

脚本会先检查 JSON 的标注类型、控件名称、类别、重复标注和图片引用，再路由到相应转换器。

## 输入

- Label Studio 导出 JSON；
- 本地原图根目录（支持递归按文件名查找）；
- 类别映射，例如 `头发=1`。像素值 `0` 固定保留为背景；
- 可选划分比例与随机种子，默认 `8:1:1`、`20261022`。

## 输出结构

```text
output/
├─ images/
│  ├─ train/
│  ├─ val/
│  └─ test/
├─ masks/
│  ├─ train/
│  ├─ val/
│  └─ test/
├─ dataset.yaml
├─ manifest.json
└─ report.json
```

- `masks` 为与原图同尺寸的单通道 PNG；
- `manifest.json` 记录任务 ID、图片和 mask 的对应关系；
- `report.json` 记录有效样本、缺图、空标注和 RLE 解码失败等情况。

## 使用示例

先检查导出结构：

```powershell
python scripts/inspect_labelstudio_export.py project.json
```

制作头发二值语义分割数据集：

```powershell
python scripts/build_semantic_brush_dataset.py `
  --input project.json `
  --image-root D:\path\to\images `
  --output D:\path\to\hair_semantic_seg_v1 `
  --class "头发=1"
```

制作 Choices 分类数据集：

```powershell
python scripts/build_classification_dataset.py `
  --input project.json `
  --image-root D:\path\to\images `
  --output D:\path\to\classification_v1 `
  --field disease_label `
  --qa-field qa_flag --qa-value QA_PASS
```

制作 YOLO 目标检测或实例分割数据集：

```powershell
python scripts/build_yolo_dataset.py `
  --input project.json `
  --image-root D:\path\to\images `
  --output D:\path\to\yolo_dataset_v1 `
  --mode detect       # PolygonLabels 时改为 seg
```

## 数据安全与校验

- 不修改原始 JSON 或原图；
- 默认拒绝覆盖非空输出目录；
- 同一任务存在重复 annotation 时选取最新一条；
- 多类别 mask 若发生像素重叠会停止并报告；
- 交付前应检查图片/mask 配对、尺寸、类别像素值及跨 split 重复情况。

## 后续计划

- `RectangleLabels → YOLO Detect / COCO`；
- `COCO` 导出；
- `KeyPointLabels → YOLO Pose / COCO Keypoints`；
- `BrushLabels` 保留独立实例的 YOLO-Seg / COCO 转换；
- 分类、框和 mask 混合标注的多任务数据集拆分。
