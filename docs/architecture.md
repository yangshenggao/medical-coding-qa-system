# 架构说明

本文档面向需要快速理解系统内部实现的开发者或后续维护者，重点说明当前项目的模块边界、检索链路和部署组成。

## 1. 总体结构

系统分为 4 层：

1. 前端交互层：`Vue 3 + Vite + Element Plus`
2. 后端服务层：`Flask + SQLAlchemy`
3. 数据与向量层：`MySQL + Chroma`
4. 模型层：`Ollama`

对应目录：

```text
项目源码/client   前端
项目源码/server   后端
知识库文件        原始词典与说明文档
docker            容器构建文件
```

## 2. 前端页面

核心业务页：

- `Home.vue`：数据概览
- `WhodrugQuery.vue`：`WHODrug` 查询
- `MeddraSearch.vue`：`MedDRA` 搜索
- `Chat.vue`：智能问答
- `DataImport.vue`：词典导入
- `ChatHistory.vue`：对话历史

当前视觉方向不是通用 AI 聊天产品，而是偏“医学信息工作台”。其中 `Chat.vue` 已调整为左右布局：

- 左侧：知识库选择
- 右侧：对话工作区、候选线索和输入区

## 3. 后端模块

入口文件：

- `app.py`：Flask 应用工厂、蓝图注册、健康检查
- `config.py`：数据库、Ollama、Chroma、解释链路参数

路由层：

- `routes/auth.py`：登录与用户信息
- `routes/knowledge_base.py`：知识库列表与管理
- `routes/document.py`：文档上传、删除、文档统计
- `routes/chat.py`：智能问答与历史记录
- `routes/user.py`：用户管理
- `routes/stats.py`：数据概览统计
- `routes/whodrug.py`：`WHODrug` 查询
- `routes/meddra.py`：`MedDRA` 搜索与语义检索
- `routes/medical_import.py`：词典导入、状态、日志

服务层：

- `services/rag_service.py`：问答主链路
- `services/vector_service.py`：文件解析、切块、向量化、检索
- `services/meddra_explain_service.py`：多 agent 风格的解释与评测链路

## 4. 数据层设计

### MySQL

用途：

- 用户、权限、聊天历史
- 结构化词典数据
- 知识库与文档记录
- 导入日志

当前业务知识库口径默认是：

- `WHODrug词典`
- `MedDRA词典`

内部规则文档资源包括：

- `MedDRA说明文档（中文）`
- `MedDRA说明文档（英文）`

### Chroma

用途：

- 存放上传文档分块后的向量
- 存放 `MedDRA` guidance 文档向量

当前默认切块参数：

- `CHUNK_SIZE = 500`
- `CHUNK_OVERLAP = 50`

## 5. 问答与检索链路

### 5.1 通用文档问答

上传文档后，系统会执行：

1. 解析文本
2. 字符级切块
3. 通过 `qwen3-embedding:0.6b` 生成向量
4. 写入 `Chroma`
5. 问答时按相似度召回相关 chunk
6. 把召回结果与问题一起交给 `qwen3:4b`

### 5.2 `WHODrug`

`WHODrug` 查询以结构化数据库检索为主，适合：

- 药品名
- 商品名
- 活性成分
- `Drug Code`
- `MPID`

### 5.3 `MedDRA`

`MedDRA` 当前是“结构化候选优先 + 语义补充”的混合方案。

当前顺序：

1. 先查 `PT`
2. 再按 `SOC -> HLGT -> HLT -> PT` 兜底
3. 最后才考虑语义补充

智能问答主链路当前保持解释型回答，不默认启用严格 `Verifier` 降级逻辑。

### 5.4 中英文分流

`MedDRA` 智能问答已做语言绑定：

- 中文问题优先中文候选和中文 guidance
- 英文问题优先英文候选和英文 guidance

这条规则主要落在 `rag_service.py` 中，避免英文提问误用中文规则说明。

## 6. 多 Agent 解释链路

`meddra_explain_service.py` 中已经实现了一套多阶段工作流，角色上包括：

- Retriever
- Generator / Hybrid Generator
- Judge
- Verifier
- Feedback loop

当前这套链路更适合：

- 深度复核
- 离线评测
- 批量解释验证

而不是默认挂在主聊天路径上。

## 7. 数据导入口径

前台当前只暴露 4 个核心导入按钮：

- `WHODrug (英文)`
- `WHODrug (中文)`
- `MedDRA (英文)`
- `MedDRA (中文)`

`SMQ` 与 `MedDRA` 说明文档后端导入能力仍在，但前台不再暴露对应按钮。导入日志与状态统计当前仍在 `DataImport.vue` 展示。

## 8. 部署拓扑

### 本地脚本

- `start_project.sh`
- `stop_project.sh`

### Docker Compose

服务组成：

- `mysql`
- `ollama`
- `backend`
- `frontend`

默认端口：

- 前端：`3000`
- 后端：`5002`
- MySQL：`3308`
- Ollama：`11434`

健康检查入口：

- `/api/health`

## 9. 当前已知技术债

- 密码存储仍使用 `MD5`
- 部分异常返回仍可进一步收口
- `DataImport.vue` 展示口径仍可继续简化
- 前端构建仍有大 chunk 告警，主要来自 `echarts` 和主 bundle
