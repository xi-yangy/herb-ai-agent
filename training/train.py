"""中草药图像分类训练脚本（单标签 / ImageFolder）。

在 PyCharm 本地独立运行（不依赖后端），使用 ResNet50（ImageNet 预训练）迁移学习，
训练完成后导出两个产物供后端识别通道加载：

- ``model.pth``   ：torch.save 保存的字典，含 ``state_dict``（模型权重）与
                    ``class_to_idx``（类别名 -> 索引映射，保证推理时类别对齐）；
- ``classes.txt`` ：每行一个类别名，行号即类别索引，与 ``class_to_idx`` 严格对应。

运行示例（GPU 自动使用，无 GPU 自动回退 CPU）：:

    python train.py --data-dir D:/Code/data --epochs 30 --out ./output

数据目录要求（ImageFolder 结构，类别名 = 文件夹名）：:

    D:/Code/data/
    ├── train/          # 必需：每类一个文件夹，内含 jpg/png
    │   ├── 人参/ *.jpg
    │   ├── 黄芪/ *.jpg
    │   └── ...
    └── val/            # 可选：验证集；缺失时从 train 按比例切分
        └── ...
"""

from __future__ import annotations

import argparse
import logging
import random
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from torch.utils.data import DataLoader, Dataset, random_split
from torchvision import datasets, models

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("train")


# ImageNet 归一化参数（ResNet 预训练约定）
_IMAGENET_MEAN = [0.485, 0.456, 0.406]
_IMAGENET_STD = [0.229, 0.224, 0.225]

# 支持的骨干网络（键为参数值，值为 torchvision 构造器 + 默认分类头输入维度）
_BACKBONES = {
    "resnet50": (models.resnet50, 2048),
    "resnet18": (models.resnet18, 512),
    "resnet34": (models.resnet34, 512),
    "mobilenet_v3": (models.mobilenet_v3_large, 1280),
}

# 输入分辨率（ResNet 等骨干默认 224）
_INPUT_SIZE = 224


def set_seed(seed: int) -> None:
    """固定随机种子，保证训练可复现。"""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def build_transforms(train: bool) -> transforms.Compose:
    """构建数据增强流水线。训练集用增强，验证集用标准 resize + 中心裁剪。"""
    if train:
        return transforms.Compose(
            [
                transforms.RandomResizedCrop(_INPUT_SIZE, scale=(0.8, 1.0)),
                transforms.RandomHorizontalFlip(),
                transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
                transforms.ToTensor(),
                transforms.Normalize(_IMAGENET_MEAN, _IMAGENET_STD),
            ]
        )
    return transforms.Compose(
        [
            transforms.Resize(256),
            transforms.CenterCrop(_INPUT_SIZE),
            transforms.ToTensor(),
            transforms.Normalize(_IMAGENET_MEAN, _IMAGENET_STD),
        ]
    )


def build_model(backbone: str, num_classes: int, freeze_backbone: bool) -> nn.Module:
    """构建分类模型：预训练骨干 + 替换分类头。"""
    if backbone not in _BACKBONES:
        raise ValueError(f"不支持的骨干网络：{backbone}，可选 {list(_BACKBONES)}")
    builder, in_features = _BACKBONES[backbone]

    if backbone == "mobilenet_v3":
        model = builder(weights=models.MobileNet_V3_Large_Weights.IMAGENET1K_V1)
        classifier = model.classifier
        model.classifier = nn.Sequential(
            classifier[0],
            classifier[1],
            classifier[2],
            nn.Linear(classifier[3].in_features, num_classes),
        )
    else:
        model = builder(weights="IMAGENET1K_V1")
        model.fc = nn.Linear(in_features, num_classes)

    if freeze_backbone:
        # 冻结除分类头外的所有参数，只训练分类头（更快、更稳）
        for name, param in model.named_parameters():
            if "fc" not in name and "classifier" not in name:
                param.requires_grad = False
    return model


def train_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
) -> tuple[float, float]:
    """训练一个 epoch，返回 (平均 loss, top-1 准确率)。"""
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0
    for images, labels in loader:
        images, labels = images.to(device), labels.to(device)
        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        running_loss += loss.item() * images.size(0)
        _, preds = torch.max(outputs, 1)
        correct += (preds == labels).sum().item()
        total += labels.size(0)

    return running_loss / total, correct / total


@torch.no_grad()
def evaluate(
    model: nn.Module, loader: DataLoader, criterion: nn.Module, device: torch.device
) -> tuple[float, float]:
    """在验证集上评估，返回 (平均 loss, top-1 准确率)。"""
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0
    for images, labels in loader:
        images, labels = images.to(device), labels.to(device)
        outputs = model(images)
        loss = criterion(outputs, labels)

        running_loss += loss.item() * images.size(0)
        _, preds = torch.max(outputs, 1)
        correct += (preds == labels).sum().item()
        total += labels.size(0)

    return running_loss / total, correct / total


def export(model: nn.Module, class_to_idx: dict[str, int], out_dir: Path) -> None:
    """导出模型权重与类别清单。"""
    out_dir.mkdir(parents=True, exist_ok=True)

    # 类别名按索引排序，保证 classes.txt 行号与 class_to_idx 一致
    idx_to_class = {idx: name for name, idx in class_to_idx.items()}
    classes = [idx_to_class[i] for i in range(len(idx_to_class))]

    torch.save(
        {"state_dict": model.state_dict(), "class_to_idx": class_to_idx},
        out_dir / "model.pth",
    )
    (out_dir / "classes.txt").write_text("\n".join(classes) + "\n", encoding="utf-8")
    logger.info("已导出产物到 %s：model.pth + classes.txt（%d 类）", out_dir, len(classes))


def main() -> int:
    parser = argparse.ArgumentParser(description="中草药图像分类训练（ImageFolder + ResNet50）")
    parser.add_argument("--data-dir", type=str, default="D:/Code/data", help="数据集根目录（含 train/、可选 val/）")
    parser.add_argument("--epochs", type=int, default=30, help="训练轮数")
    parser.add_argument("--batch-size", type=int, default=32, help="批次大小")
    parser.add_argument("--lr", type=float, default=1e-3, help="初始学习率")
    parser.add_argument("--model", type=str, default="resnet50", help="骨干网络（resnet50/resnet18/resnet34/mobilenet_v3）")
    parser.add_argument("--freeze", action="store_true", help="冻结骨干只训练分类头（默认全量微调）")
    parser.add_argument("--val-split", type=float, default=0.2, help="无 val/ 目录时，从 train 划分给验证集的比例")
    parser.add_argument("--num-workers", type=int, default=4, help="数据加载线程数")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    parser.add_argument("--out", type=str, default="./output", help="产物输出目录")
    args = parser.parse_args()

    set_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("使用设备：%s", device)
    if device.type == "cuda":
        logger.info("GPU：%s", torch.cuda.get_device_name(0))

    data_dir = Path(args.data_dir)
    train_dir = data_dir / "train"
    val_dir = data_dir / "val"
    if not train_dir.is_dir():
        logger.error("找不到训练目录：%s", train_dir)
        return 1

    # 加载数据集：先加载 train（含所有类别），验证集优先用 val/，缺失则从 train 切分
    full_train = datasets.ImageFolder(train_dir, transform=build_transforms(True))
    num_classes = len(full_train.classes)
    logger.info("类别数：%d", num_classes)
    logger.info("类别名：%s", ", ".join(full_train.classes))

    if val_dir.is_dir():
        val_dataset = datasets.ImageFolder(val_dir, transform=build_transforms(False))
        # 校验验证集类别与训练集一致
        if val_dataset.classes != full_train.classes:
            logger.warning("验证集类别与训练集不一致，将改用训练集切分验证集")
            val_dataset = None
    else:
        val_dataset = None

    if val_dataset is None:
        val_size = int(len(full_train) * args.val_split)
        train_size = len(full_train) - val_size
        train_dataset, val_dataset = random_split(
            full_train, [train_size, val_size],
            generator=torch.Generator().manual_seed(args.seed),
        )
        logger.info("无 val/ 目录，按 %.0f%% 切分：train=%d / val=%d", args.val_split * 100, train_size, val_size)
    else:
        train_dataset = full_train
        logger.info("使用独立 val/ 目录：train=%d / val=%d", len(train_dataset), len(val_dataset))

    train_loader = DataLoader(
        train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=args.num_workers, pin_memory=device.type == "cuda"
    )
    val_loader = DataLoader(
        val_dataset, batch_size=args.batch_size, shuffle=False, num_workers=args.num_workers, pin_memory=device.type == "cuda"
    )

    model = build_model(args.model, num_classes, args.freeze)
    model = model.to(device)

    criterion = nn.CrossEntropyLoss()
    # 仅优化可训练参数（freeze 时分类头参数）
    optimizer = torch.optim.Adam(filter(lambda p: p.requires_grad, model.parameters()), lr=args.lr)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    best_acc = 0.0
    for epoch in range(1, args.epochs + 1):
        train_loss, train_acc = train_one_epoch(model, train_loader, criterion, optimizer, device)
        val_loss, val_acc = evaluate(model, val_loader, criterion, device)
        scheduler.step()

        logger.info(
            "Epoch %d/%d | train loss %.4f acc %.2f%% | val loss %.4f acc %.2f%%",
            epoch, args.epochs, train_loss, train_acc * 100, val_loss, val_acc * 100,
        )

        if val_acc > best_acc:
            best_acc = val_acc
            # 立即保存当前最优权重（覆盖），并记住类别映射
            torch.save(
                {"state_dict": model.state_dict(), "class_to_idx": full_train.class_to_idx},
                Path(args.out) / "model.pth",
            )
            logger.info("  -> 保存新的最优权重（val acc %.2f%%）", best_acc * 100)

    Path(args.out).mkdir(parents=True, exist_ok=True)
    # 最终导出 classes.txt（无论是否保存了 best，确保类别清单一定产出）
    idx_to_class = {idx: name for name, idx in full_train.class_to_idx.items()}
    classes = [idx_to_class[i] for i in range(len(idx_to_class))]
    (Path(args.out) / "classes.txt").write_text("\n".join(classes) + "\n", encoding="utf-8")

    logger.info("训练完成，最终最优验证准确率：%.2f%%", best_acc * 100)
    logger.info("产物位置：%s（model.pth + classes.txt）", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
