# 劳动合同纠纷智能问答系统

> 基于 RAG + LoRA 微调的劳动法智能问答系统，帮助劳动者快速获取法律指引、了解维权途径。

## 项目简介

本项目是一个面向劳动合同纠纷场景的智能问答系统，核心解决的问题是：**劳动者使用日常口语（如"被辞退""没签合同双倍工资"）提问时，系统能精准匹配到对应的法律条文，并给出可操作的维权指引。**

系统通过 LoRA 微调 Sentence-BERT 模型，提升劳动法术语同义词的语义匹配能力，使检索系统不仅能理解法律术语，还能理解劳动者的日常表达。

---

## 核心功能

1. **智能问答**：用户用自然语言提问，系统检索相关法条并生成回答
2. **同义词理解**：通过 LoRA 微调，将"试用期"匹配到"考察期""试工期间"等同义表达
3. **法条检索**：基于向量相似度检索，精准定位到具体法条
4. **维权指引**：按场景分类的行动步骤指引（试用期纠纷/违法解除/加班费/竞业限制/双倍工资/经济补偿）
5. **落地服务**：提供 12333/12348/12315 等真实热线电话和各省法律援助网址

---

## 技术栈

| 组件 | 技术选型 | 说明 |
|------|---------|------|
| 嵌入模型 | BAAI/bge-large-zh-v1.5 | 中文语义向量模型 |
| 微调方法 | PEFT (LoRA) | 参数高效微调，r=8, alpha=16 |
| 向量数据库 | Milvus 2.4 | 法律条文向量存储与检索 |
| 关系数据库 | PostgreSQL 15 | 用户、法条、对话历史存储 |
| 后端框架 | FastAPI | 高性能异步 Web 框架 |
| 前端服务 | Nginx | 静态文件服务 + API 反向代理 |
| LLM API | DeepSeek | 训练数据生成 + 智能问答 |
| 容器化 | Docker Compose | 一键编排所有服务 |

---

## 项目结构

```
labor-law-qa-system/
├── scripts/                          # 脚本目录
│   ├── generate_train_data.py        # DeepSeek API 生成同义词训练数据
│   ├── train_lora.py                 # LoRA 微调 Sentence-BERT
│   ├── eval_model.py                 # 模型评估（微调前后对比）
│   ├── init_db.py                    # 数据库初始化（建表+法条数据）
│   └── ingest_laws.py                # 法条向量化导入 Milvus
├── data/                             # 数据目录
│   ├── legal_terms.json              # 200个劳动法术语词表
│   ├── synonym_dict.json             # 42个术语的同义词词典
│   ├── sample_laws.json              # 12条真实法条原文
│   └── landing_services.json         # 落地服务数据（热线+网址+行动指引）
├── models/                           # 模型目录
│   └── legal-lora-model/             # LoRA 微调后的模型权重
├── docker-compose.yml                # Docker 编排文件
├── Dockerfile.backend                # 后端 Dockerfile
├── Dockerfile.frontend               # 前端 Dockerfile（多阶段构建）
├── nginx.conf                        # Nginx 配置
├── requirements-backend.txt          # 后端 Python 依赖
├── .env.example                      # 环境变量示例
└── README.md                         # 项目说明文档
```

---

## 快速开始

### 前置要求

- Docker & Docker Compose
- Python 3.10+（本地运行脚本时需要）
- DeepSeek API Key（用于生成训练数据，[获取地址](https://platform.deepseek.com/)）

### 方式一：Docker 一键部署

```bash
# 1. 克隆项目
cd /workspace/labor-law-qa-system

# 2. 复制环境变量配置
cp .env.example .env

# 3. 编辑 .env，填入你的 DeepSeek API Key
vi .env

# 4. 启动所有服务
docker-compose up -d

# 5. 初始化数据库
docker exec labor-law-backend python scripts/init_db.py

# 6. 向量化导入法条到 Milvus
docker exec labor-law-backend python scripts/ingest_laws.py
```

服务启动后：
- 前端：http://localhost
- 后端 API 文档：http://localhost/docs
- 健康检查：http://localhost/health

### 方式二：本地开发运行

#### 1. 安装 Python 依赖

```bash
pip install -r requirements-backend.txt
```

#### 2. 配置环境变量

```bash
export DEEPSEEK_API_KEY="your_api_key_here"
export DATABASE_URL="postgresql://labor:labor123@localhost:5432/labor_law"
export MILVUS_HOST="127.0.0.1"
export MILVUS_PORT="19530"
```

#### 3. 启动 PostgreSQL 和 Milvus

```bash
# 仅启动数据库和向量库
docker-compose up -d postgres milvus etcd minio
```

#### 4. 生成训练数据

```bash
# 使用 DeepSeek API 为200个术语生成同义词
python scripts/generate_train_data.py

# 如无 API Key，脚本将仅使用本地同义词词典生成数据
```

#### 5. LoRA 微调模型

```bash
python scripts/train_lora.py
```

训练过程会打印训练前后的相似度对比，预期效果：
- 正样本（同义词对）相似度提升
- 负样本（不同概念）相似度下降
- 区分度（正-负）显著增大

#### 6. 评估模型

```bash
python scripts/eval_model.py
```

输出微调前后的详细对比表格，包含 25 个测试术语对。

#### 7. 初始化数据库

```bash
python scripts/init_db.py
```

创建所有表并插入：
- 默认管理员账号（admin / admin123）
- 12条真实法条数据

#### 8. 向量化导入法条

```bash
python scripts/ingest_laws.py
```

将法条文本通过 BGE 模型向量化后存入 Milvus，导入完成后会自动执行一次检索验证。

---

## 数据说明

### 法条数据（data/sample_laws.json）

包含以下法律法规的真实原文：

| 法律法规 | 条文 |
|---------|------|
| 《劳动合同法》 | 第19条（试用期期限）、第20条（试用期工资）、第21条（试用期解除限制）、第37条（劳动者辞职）、第39条（过失性解除）、第46条（经济补偿情形）、第47条（经济补偿计算）、第82条（二倍工资）、第87条（违法解除赔偿金）|
| 《劳动争议调解仲裁法》 | 第6条（举证责任）、第27条（仲裁时效）|
| 法释〔2025〕12号 | 第19条（约定无需缴纳社保的效力）|

### 同义词词典（data/synonym_dict.json）

包含 42 个劳动法术语的民间俗称/同义映射，例如：
- 试用期 -> 考察期 / 试工期间 / 实习期
- 辞退 -> 解除劳动合同 / 开除 / 终止劳动关系
- 加班费 -> 延时劳动报酬 / 延时工资
- 竞业限制 -> 竞业禁止 / 同业禁止

### 落地服务数据（data/landing_services.json）

包含真实的维权热线和网址：
- 12333 全国人社服务热线
- 12348 公共法律服务热线（http://www.12348.gov.cn）
- 12315 消费投诉热线（https://www.12315.cn）
- 各省法律援助网址（北京/上海/广东/江苏等 10 个省份）
- 6 类场景的行动指引（试用期纠纷/违法解除/加班费/竞业限制/双倍工资/经济补偿）

---

## LoRA 微调架构

```
预训练模型 BAAI/bge-large-zh-v1.5
        |
        v
    +---+---+
    | Query |  <-- LoRA Adapter (r=8, alpha=16)
    | Value |  <-- LoRA Adapter (r=8, alpha=16)
    +---+---+
        |
        v
   句向量输出 (1024维)
        |
        v
   CosineSimilarityLoss
```

LoRA 微调仅训练 query 和 value 投影矩阵的低秩适配器，大幅减少可训练参数量（约占总参数的 0.1%），同时达到接近全量微调的效果。

---

## 创新点

1. **同义词扩召回**：通过 LoRA 微调使模型理解劳动法术语的民间俗称，解决"用户说人话，系统查法条"的语义鸿沟问题

2. **真实法条驱动**：所有法条数据均使用法律原文，非编造内容，确保回答的法律准确性

3. **闭环维权指引**：不仅回答法律问题，还提供从收集证据到申请仲裁的完整行动步骤，并链接到 12348 等真实落地服务

4. **参数高效微调**：使用 LoRA 技术（r=8），在单卡 GPU 上即可完成微调，训练成本极低

5. **双库架构**：PostgreSQL 存结构化数据（用户/法条/对话历史），Milvus 存向量数据（法条语义向量），各司其职

---

## 默认账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 管理员 |

> 安全提示：请在首次登录后立即修改默认密码！

---

## API 接口概览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/login | 用户登录 |
| POST | /api/chat/ask | 智能问答（输入问题，返回法条+回答+维权指引） |
| GET | /api/laws/search | 关键词搜索法条 |
| GET | /api/services/hotlines | 获取落地服务热线 |
| GET | /api/services/action-guide/{scenario} | 获取场景化行动指引 |
| POST | /api/feedback | 提交用户反馈 |
| GET | /health | 健康检查 |

---

## 常见问题

**Q: 没有 DeepSeek API Key 能运行吗？**
A: 可以。`generate_train_data.py` 会检测到无 API Key 后，仅使用本地同义词词典（synonym_dict.json）生成训练数据，仍可完成 LoRA 微调。

**Q: 首次运行时模型下载很慢怎么办？**
A: BAAI/bge-large-zh-v1.5 模型约 1.3GB，可通过设置 HuggingFace 镜像加速：
```bash
export HF_ENDPOINT=https://hf-mirror.com
```

**Q: Docker 启动后 Milvus 健康检查不通过？**
A: Milvus 首次启动需要初始化 etcd 和 MinIO，可能需要等待 30-60 秒。请检查日志：
```bash
docker logs labor-law-milvus
```

**Q: 如何添加更多法条？**
A: 编辑 `data/sample_laws.json`，按现有格式添加新的法条条目，然后重新运行 `init_db.py` 和 `ingest_laws.py`。

---

## 许可证

本项目仅用于学习和研究目的。法条数据来源于公开的法律法规文本，不构成法律建议。具体法律问题请咨询专业律师或拨打 12348 公共法律服务热线。
