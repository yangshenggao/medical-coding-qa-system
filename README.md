# 医学编码问答系统

基于 LangChain RAG 的医学编码智能问答系统（Flask + Vue3 + Ollama + ChromaDB）

## 功能特性

- **WHODrug 药物编码查询**：支持中英文药品名、Drug Code、MPID、活性成分检索
- **MedDRA 术语搜索**：结构化查询 + 语义搜索，支持影像描述等口语化输入推荐编码
- **SMQ 标准化查询**：MedDRA 标准化查询组导入与检索
- **智能问答（RAG + LLM）**：基于知识库文档的检索增强生成问答
- **规则文档向量化**：SMQ 指南、MedDRA 入门指南等 PDF 文档自动切块向量化

## 技术栈

- 后端：Flask + SQLAlchemy + LangChain + ChromaDB
- 前端：Vue 3 + Element Plus + ECharts + Vite
- LLM：Ollama（qwen3:4b）
- Embedding：qwen3-embedding:0.6b
- 数据库：MySQL 8.0

## 快速开始

### 本地运行

```bash
./start_project.sh   # 一键启动
./stop_project.sh    # 一键停止
```

### Docker 部署

```bash
docker compose up -d
```

## 默认账号

- 用户名：admin
- 密码：123456

## 项目结构

```
项目源码/
├── client/          # Vue3 前端
│   └── src/
│       ├── views/   # 页面组件
│       └── api/     # API 接口
└── server/          # Flask 后端
    ├── routes/      # 路由
    ├── models/      # 数据模型
    ├── services/    # 业务服务（RAG、向量化）
    └── utils/       # 工具函数
```
