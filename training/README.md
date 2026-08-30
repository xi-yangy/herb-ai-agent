# 中草药图像分类训练说明

本目录用于在 PyCharm 本地独立训练一个中草药图像分类模型（单标签），训练产物将交给后端识别通道作为「本地主通道」使用。

## 1. 数据准备

数据集需为 ImageFolder 结构（类别名 = 文件夹名），例如你的 `D:/Code/data`：

```
D:/Code/data/
├── train/          # 必需：每类一个文件夹，内含 jpg/png
│   ├── 人参/ *.jpg
│   ├── 黄芪/ *.jpg
│   └── ...
└── val/            # 可选：验证集；缺失时脚本自动从 train 按比例切分
    └── ...
```

注意：
- `data.yaml` 是 YOLO 训练用的标注文件，本脚本**不会读取**它，类别以 `train/` 目录下实际存在的文件夹为准；
- 每个类别的样本数建议 ≥ 20 张，越多越稳；
- 图片格式支持 jpg/png（Pillow 能读即可）。

## 2. 安装依赖

在 PyCharm 终端（或命令行）中执行：

```bash
pip install -r requirements-training.txt
```

> 如需 GPU 加速，请先确认已安装与你的 CUDA 版本匹配的 PyTorch。若不确定，可访问
> https://pytorch.org/get-started/locally/ 按向导选择对应命令安装。

## 3. 运行训练

```bash
python train.py --data-dir D:/Code/data --epochs 30 --out ./output
```

训练脚本会自动：
- 检测 GPU（有 CUDA 用 GPU，否则回退 CPU）；
- 加载 `train/` 与 `val/`（或从 train 按 20% 切分验证集）；
- 每轮打印训练/验证的 loss 与 top-1 准确率，并保存验证准确率最高的权重。

### 常用参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--data-dir` | `D:/Code/data` | 数据集根目录 |
| `--epochs` | `30` | 训练轮数 |
| `--batch-size` | `32` | 批次大小（显存不足可调小，如 16） |
| `--lr` | `1e-3` | 初始学习率 |
| `--model` | `resnet50` | 骨干：resnet50 / resnet18 / resnet34 / mobilenet_v3 |
| `--freeze` | 关 | 加此开关则冻结骨干只训练分类头（更快更稳，适合小数据） |
| `--val-split` | `0.2` | 无 `val/` 目录时从 train 划分验证集的比例 |
| `--num-workers` | `4` | 数据加载线程数 |
| `--seed` | `42` | 随机种子 |
| `--out` | `./output` | 产物输出目录 |

## 4. 训练产物

训练完成后，`--out` 目录下会生成：

```
output/
├── model.pth      # 模型权重（含 state_dict 与 class_to_idx）
└── classes.txt    # 每行一个类别名，行号 = 类别索引
```

### 类别对齐规范（重要）

- `classes.txt` 的行号与 `model.pth` 内的 `class_to_idx` **严格一致**，后端推理时按此建立「索引 → 类别名」映射；
- **训练完成后请勿手动修改 `classes.txt` 的内容或顺序**；
- 类别名尽量与后端知识库 `Herb.name` 一致（如「人参」「黄芪」）。若个别命名有差异（如「黄芪片」），后端会通过去后缀（片/根/皮/子 等）逻辑兜底匹配。

## 5. 训练完成后

把 `output/` 目录下的 `model.pth` 与 `classes.txt` 两个文件交给后端接入（阶段二），届时会将其放入识别通道作为本地主通道，置信度低于阈值时自动回退百度识别。

## 6. 常见问题

- **报 CUDA out of memory**：调小 `--batch-size`（如 16），或加 `--freeze` 冻结骨干。
- **无 GPU**：脚本会自动回退 CPU，只是训练变慢，可考虑 `--model resnet18`。
- **类别数不对**：确认 `train/` 目录下只有类别文件夹，没有多余的杂项文件（如 `.cache`、`.txt` 标注文件会被 ImageFolder 忽略，但多余的子目录会被当成新类别）。

## 7. 百科页示例缩略图（辅助脚本）

百科页每味药材展示一张示例缩略图（位于 `backend/static/herb_imgs/<药名>.jpg`，由后端
`/api/static` 静态服务提供），由以下两个脚本生成：

**1) `export_samples.py`：训练集选图**

从训练集每类抽取 1 张代表图（固定 seed 可复现、幂等覆盖），中心裁剪 + 缩放 320px 输出：

```bash
python training/export_samples.py            # 默认读取 D:/Code/data，输出 93 张
python training/export_samples.py --seed 7   # 换一组选图结果
```

**2) `fetch_missing_images.py`：缺图药材网络抓图**

数据库 172 味药材中训练集没有对应类别的部分，通过 360 图片（主源）/ 必应 / 百度（备源）
搜索各抓 1 张示例图。脚本自动过滤水印风险 URL、校验图片可用性，失败名单记录并可重跑：

```bash
python training/fetch_missing_images.py --probe   # 探针：只取候选不下载，验证源可用
python training/fetch_missing_images.py           # 实际抓取（缺图名单自动计算，已存在文件跳过）
```

> **合规声明**：网络抓取图片仅用于本项目教学演示展示，来源为网络公开搜索结果，版权归原作者
> 所有；如用于商业用途请替换为获得授权的图片。训练集图片仅每类取 1 张示例，不整集复制。
