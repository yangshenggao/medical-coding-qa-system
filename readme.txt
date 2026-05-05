医学编码问答系统 MVP 说明

一、当前 MVP 已具备的能力
1. WHODrug 药物编码查询
2. MedDRA 关键词搜索
3. MedDRA 语义搜索候选推荐
4. 智能问答（支持 WHODrug / MedDRA 词典问答）
5. 词典导入后台页面

二、词典目录
项目默认从以下目录读取词典：
知识库文件/

其中已适配：
1. 知识库文件/WHODrug Global 2026 Mar 1
2. 知识库文件/WHODrug Global Chinese 2026 Mar 1
3. 知识库文件/English_29_0
4. 知识库文件/Chinese_29_0

如果要改目录，可设置环境变量：
MEDICAL_DICT_DIR=/你的词典目录

三、数据库
默认数据库名：
db_medical_coding

初始化脚本：
项目源码/server/sql/init.sql

四、Ollama 模型
建议至少准备：
1. qwen3:4b
2. qwen3-embedding:0.6b

示例：
ollama pull qwen3:4b
ollama pull qwen3-embedding:0.6b

五、启动方式
方式 A：一键启动
./start_project.sh

关闭：
./stop_project.sh

方式 B：手动启动
1. 启动 MySQL，并导入 项目源码/server/sql/init.sql
2. 启动 Ollama
3. 后端：
   cd 项目源码/server
   python app.py
4. 前端：
   cd 项目源码/client
   npm install
   npm run dev

六、首次使用流程
1. 登录系统
2. 管理员进入“数据导入”
3. 依次导入：
   WHODrug 中文
   WHODrug 英文
   MedDRA 中文
   MedDRA 英文
4. 导入成功后开始使用：
   WHODrug 查询
   MedDRA 搜索
   智能问答

七、MVP 说明
1. MedDRA 语义搜索返回的是候选术语推荐，不是自动最终编码
2. WHODrug 查询结果建议结合药品名、成分、国家、剂型人工复核
3. 当前版本重点是“可导入、可检索、可问答”的 MVP
