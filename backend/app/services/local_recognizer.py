"""本地自训练模型（PyTorch）识别实现。

加载训练侧导出的 ``model.pth``（含 state_dict + class_to_idx）与 ``classes.txt``
（每行一个类别名，行号=类别索引），对 base64 图片做预处理 → 推理 → softmax → top-k，
输出类别名与置信度，并复用 recognizer 模块的 ``_match_herb`` / ``_build_similar_from_names``
匹配知识库与构建相似品种。

模型懒加载 + 全局单例复用，避免每次请求重复加载；未启用 / 模型或类别文件缺失 /
推理异常时抛出异常，由 HybridRecognizer 调度器捕获后回退百度，保证链路不中断。
"""

from __future__ import annotations

import base64
import io
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.schemas.herb import HerbResponse
from app.schemas.recognize import RecognizeResult
from app.services.recognizer import (
    RecognitionService,
    _build_similar_from_names,
    _match_herb,
)

logger = logging.getLogger(__name__)

# 输入分辨率与归一化参数（与训练侧 build_transforms 保持一致）
_INPUT_SIZE = 224
_IMAGENET_MEAN = [0.485, 0.456, 0.406]
_IMAGENET_STD = [0.229, 0.224, 0.225]


class LocalRecognizer(RecognitionService):
    """本地 PyTorch 图像分类识别器。

    作为识别主通道（channel="local"）。仅在配置启用且模型/类别文件就绪时可用；
    否则 recognize 抛错，由上层调度器回退百度。
    """

    channel = "local"

    def __init__(self) -> None:
        self._model = None
        self._device = None
        self._classes: list[str] = []
        self._transform = None
        self._loaded = False

    def _resolve_device(self):
        """解析推理设备：优先配置指定，否则 cuda 可用即用 cuda，最后 cpu。"""
        import torch

        if settings.local_device:
            return torch.device(settings.local_device)
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def _load(self) -> None:
        """懒加载模型与类别清单（仅首次调用时执行）。"""
        if self._loaded:
            return

        model_path = Path(settings.local_model_path)
        classes_path = Path(settings.local_classes_path)
        if not settings.local_enabled:
            raise RuntimeError("本地模型未启用（local_enabled=false）")
        if not model_path.is_file():
            raise FileNotFoundError(f"本地模型权重文件不存在：{model_path}")
        if not classes_path.is_file():
            raise FileNotFoundError(f"本地类别清单文件不存在：{classes_path}")

        import torch
        import torchvision.models as models
        import torchvision.transforms as transforms

        # 读取类别清单（行号=类别索引），行首尾去空白
        classes = [
            line.strip() for line in classes_path.read_text(encoding="utf-8").splitlines() if line.strip()
        ]
        if not classes:
            raise ValueError(f"类别清单为空：{classes_path}")

        # 加载权重（state_dict + class_to_idx），并据此重建模型
        ckpt = torch.load(model_path, map_location="cpu")
        state_dict = ckpt.get("state_dict", ckpt)
        num_classes = len(classes)

        # 后端统一用 resnet50 结构重建（与训练默认骨干一致）
        model = models.resnet50(weights=None)
        model.fc = torch.nn.Linear(model.fc.in_features, num_classes)
        model.load_state_dict(state_dict)
        model.eval()

        device = self._resolve_device()
        model = model.to(device)

        transform = transforms.Compose(
            [
                transforms.Resize(256),
                transforms.CenterCrop(_INPUT_SIZE),
                transforms.ToTensor(),
                transforms.Normalize(_IMAGENET_MEAN, _IMAGENET_STD),
            ]
        )

        self._model = model
        self._device = device
        self._classes = classes
        self._transform = transform
        self._loaded = True
        logger.info("本地模型已加载（%d 类，设备 %s）", num_classes, device)

    def _predict(self, image_base64: str) -> list[tuple[str, float]]:
        """对 base64 图片做推理，返回按置信度降序的 top-k (类别名, 置信度)。"""
        import torch
        import torch.nn.functional as F
        from PIL import Image

        self._load()

        # 去除 data:image 前缀后解码为图片
        if "," in image_base64:
            image_base64 = image_base64.split(",", 1)[1]
        raw = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(raw)).convert("RGB")

        tensor = self._transform(image).unsqueeze(0).to(self._device)
        with torch.no_grad():
            logits = self._model(tensor)
            probs = F.softmax(logits, dim=1)[0]

        # 取 top-k（k 不超过类别总数）
        k = min(settings.local_top_k, len(self._classes))
        top_probs, top_idx = torch.topk(probs, k)
        return [
            (self._classes[int(i)], float(p)) for p, i in zip(top_probs, top_idx)
        ]

    def recognize(self, image_base64: str, db: Session) -> RecognizeResult:
        """识别图片；未启用/加载失败/推理异常时抛错，由调度器回退。"""
        topk = self._predict(image_base64)
        if not topk:
            raise RuntimeError("本地模型推理无结果")

        name, score = topk[0]
        herb = _match_herb(db, name)
        similar = _build_similar_from_names(db, topk)

        low_conf = score < settings.local_confidence_threshold
        if low_conf:
            logger.info("本地模型置信度偏低（%.2f），交由调度器回退百度", score)

        return RecognizeResult(
            name=name,
            confidence=round(float(score), 4),
            safety_level=herb.safety_level if herb else "普通",
            channel=self.channel,
            similar=similar,
            low_confidence=low_conf,
            herb=HerbResponse.model_validate(herb) if herb else None,
        )
