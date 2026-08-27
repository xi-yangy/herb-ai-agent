# 多模态中草药图像识别智能体

> 一款面向大众消费者与中医药从业者的**多模态中草药图像识别智能体**，通过拍照/上传图片快速识别中草药（含干燥药材与饮片），并提供功效、禁忌、安全提示与药典级专业信息。

> **合规声明**：本项目的识别/查询结果仅供参考，不构成诊断或处方建议，如有不适请咨询执业医师/药师。

---

## 项目简介

- **技术栈**：前端 Vue 3 + Vant + Tailwind CSS；后端 Python FastAPI；数据存储 SQLite（起步）→ MySQL。
- **识别引擎**：混合双通道——自建模型（主）+ 百度植物识别 API（兜底）。
- **产品形态**：Web/H5，移动优先 + 桌面端大屏适配（响应式）。

详细需求见 [`docs/`](./docs/)（需求文档 v0.4 与 PRD v1.0）。开发以 **PRD v1.0** 为唯一执行依据。

---

## 目录结构

```
.
├── CODEBUDDY.md          # 项目宪章与协作基线
├── docs/                 # 需求文档 / PRD
├── frontend/             # Vue 3 前端（Vant + Tailwind）
│   └── src/              # 源码（views/router/stores/api/components）
├── backend/              # FastAPI 后端
│   ├── app/              # 应用源码（routers/models/schemas/services/core/db）
│   ├── tests/            # pytest 冒烟测试
│   ├── requirements.txt  # 运行依赖
│   ├── requirements-dev.txt  # 开发依赖
│   ├── run.py            # 启动入口
│   └── .env.example      # 环境变量样例
└── datasets/             # 药材图像数据集（不提交，见 .gitignore）
```

---

## 环境要求

| 依赖 | 版本 |
| --- | --- |
| Node.js | ≥ 20 |
| npm | ≥ 10 |
| Python | **3.12**（后端；3.14 尚不被 pydantic-core 支持） |
| Git | ≥ 2.x |

---

## 快速开始

### 后端（FastAPI）

```bash
cd backend
py -3.12 -m venv .venv              # 创建虚拟环境
.venv\Scripts\activate              # 激活（Windows PowerShell）
pip install -r requirements-dev.txt # 安装依赖（含测试）
python run.py                       # 启动服务（默认 0.0.0.0:8000）
```

启动后访问：
- 接口文档：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/api/health

> 注意：后端需使用 Python 3.12（pydantic-core 在 3.14 下无预编译 wheel，会构建失败）。

### 前端（Vue 3 + Vant + Tailwind）

```bash
cd frontend
npm install
npm run dev     # 启动开发服务器（默认 127.0.0.1:5173）
```

启动后访问：http://127.0.0.1:5173/

### 前后端联调

前端已配置 Vite 代理：`/api` 请求自动转发到 `http://127.0.0.1:8000`。
**需先启动后端**，再启动前端，即可通过前端页面访问后端接口。

> 提示：若 npm 安装或网络受限，需为 npm 配置代理（如本机 Clash）：
> `npm config set proxy http://127.0.0.1:7897`、`npm config set https-proxy http://127.0.0.1:7897`

---

## 协作规范

### 分支策略

| 分支 | 用途 |
| --- | --- |
| `main` | 稳定分支，可演示版本 |
| `dev` | 集成分支，日常开发合并目标 |
| `feature/*` | 功能分支，从 `dev` 切出，完成后合回 `dev` |

### 提交规范

- 提交信息简洁说明变更意图，格式建议：`<type>: <简述>`（如 `feat: 新增识别接口`、`fix: 修复高危警示判定`、`docs: 更新 README`）。
- **不提交**生成物与临时文件（`node_modules`、`venv`、训练缓存、内网穿透日志等，已在 `.gitignore` 排除）。

### 工作约定

1. **文档驱动**：需求/设计变更先更新文档，再进入开发；PRD 为开发唯一执行依据，不自行新增功能。
2. **合规优先**：任何代码/文案不得出现诊断/处方性表述；高危警示逻辑（不可跳过）为硬性要求。
3. **不虚标**：识别范围、准确率等以实际验证结果如实标注。

---

## 远程仓库

- 远程地址：https://github.com/xi-yangy/herb-ai-agent.git（私有）
- 推送：`git push origin main`

---

**文档版本**：0.1（骨架阶段）
**创建时间**：2026-08-27
