# AGENTS

本文件面向后续接手本仓库的 AI / Agent，记录当前项目结构、关键约定和容易踩坑的实现口径。

## 项目概览

- 项目名称：医学编码问答系统
- 前端：`项目源码/client`
- 后端：`项目源码/server`
- 数据源目录：`知识库文件`
- 部署方式：
  - 本地脚本：`start_project.sh`、`stop_project.sh`
  - 容器编排：`docker-compose.yml`

## 关键运行口径

- 前端默认端口：`3000`
- 后端默认端口：`5002`
- 本地 MySQL 默认端口：`3308`
- Ollama 默认端口：`11434`
- 后端健康检查：`/api/health`
- Docker 默认模型：
  - `qwen3:4b`
  - `qwen3-embedding:0.6b`

## 前端结构

- `src/views/Layout.vue`：整体后台框架
- `src/views/Home.vue`：数据概览页
- `src/views/WhodrugQuery.vue`：`WHODrug` 查询
- `src/views/MeddraSearch.vue`：`MedDRA` 搜索
- `src/views/Chat.vue`：智能问答
- `src/views/DataImport.vue`：词典导入

### 当前前端设计方向

- 整体风格已从通用后台模板切到偏“医学编辑部 / 专业信息工作台”
- 视觉基调：暖纸色背景、深墨绿主色、锈红与黄铜做强调
- 不走常见 AI 聊天产品的发光渐变路线

### 智能问答页当前约定

- 采用左右布局：
  - 左侧：知识库选择
  - 右侧：对话工作区
- 页面说明文案放在 `智能问答` 标题下方
- 对应 Figma 设计文件：
  - file key：`GV0fd7GivMuwFAw53x8glF`
  - 文件名：`智能问答-页面布局优化-设计稿`

## 后端结构

- `app.py`：Flask 应用入口与蓝图注册
- `config.py`：环境变量、数据库、Ollama、Chroma 与解释链路参数
- `routes/`
  - `auth.py`
  - `knowledge_base.py`
  - `document.py`
  - `chat.py`
  - `user.py`
  - `stats.py`
  - `whodrug.py`
  - `meddra.py`
  - `medical_import.py`
- `services/`
  - `rag_service.py`
  - `vector_service.py`
  - `meddra_explain_service.py`

## 检索与问答约定

### 通用 RAG

- 上传文档经解析、切块、向量化后写入 `Chroma`
- 当前默认切块参数：
  - `CHUNK_SIZE = 500`
  - `CHUNK_OVERLAP = 50`

### `WHODrug`

- 以结构化数据库查询为主
- 适合药品名、商品名、活性成分、`Drug Code`、`MPID`

### `MedDRA`

- 智能问答和检索以结构化候选优先
- 当前顺序：
  - 先查 `PT`
  - 再按 `SOC -> HLGT -> HLT -> PT` 兜底
  - 之后才考虑语义补充
- 英文提问应优先英文候选和英文 guidance
- 中文提问应优先中文候选和中文 guidance

### 多 Agent 相关

- `meddra_explain_service.py` 内已有 `Retriever / Generator / Judge / Verifier / Feedback loop`
- 这套多 agent 当前更适合作为深度复核或离线评测能力
- 主智能问答链路当前没有默认挂严格 `Verifier`，因为会削弱解释性

## 数据导入口径

- 前台当前仅暴露 4 个核心导入按钮：
  - `WHODrug (英文)`
  - `WHODrug (中文)`
  - `MedDRA (英文)`
  - `MedDRA (中文)`
- `SMQ` 与 `MedDRA` 说明文档后端能力仍在，但前台不再提供对应导入按钮
- `DataImport.vue` 当前仍展示：
  - 数据状态统计
  - 导入日志表格

## 统计口径

- 业务知识库默认理解为：
  - `WHODrug词典`
  - `MedDRA词典`
- `MedDRA说明文档（中文/英文）` 属于内部规则文档资源
- 首页文档总数和知识库文档占比已改为按 `t_document` 实时聚合，不再依赖失真的 `doc_count` 缓存字段

## 已知后续优化点

- 密码存储仍是 `MD5`，需要升级到更安全方案
- 后端仍有部分异常信息返回可以进一步收口
- `DataImport.vue` 的展示口径还可以继续收窄
- 前端产物仍有大 chunk 告警，主要来自 `echarts` 和主 bundle

## 常用验证命令

前端构建：

```bash
cd 项目源码/client
npm run build
```

后端健康检查：

```bash
curl http://127.0.0.1:5002/api/health
```

容器配置检查：

```bash
docker compose config
```
