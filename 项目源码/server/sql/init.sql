-- ============================================
-- 医学编码问答系统 - 数据库初始化脚本
-- 数据库名: db_medical_coding
-- ============================================

CREATE DATABASE IF NOT EXISTS db_medical_coding DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE db_medical_coding;

-- 用户表
DROP TABLE IF EXISTS t_import_log;
DROP TABLE IF EXISTS t_meddra_smq_term;
DROP TABLE IF EXISTS t_meddra_smq;
DROP TABLE IF EXISTS t_meddra;
DROP TABLE IF EXISTS t_whodrug;
DROP TABLE IF EXISTS t_chat_history;
DROP TABLE IF EXISTS t_document;
DROP TABLE IF EXISTS t_knowledge_base;
DROP TABLE IF EXISTS t_user;

CREATE TABLE t_user (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '用户ID',
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    password VARCHAR(255) NOT NULL COMMENT '密码（哈希存储）',
    nickname VARCHAR(50) DEFAULT '' COMMENT '昵称',
    role VARCHAR(10) NOT NULL DEFAULT 'user' COMMENT '角色：admin-管理员，user-普通用户',
    avatar VARCHAR(255) DEFAULT '' COMMENT '头像地址',
    status TINYINT NOT NULL DEFAULT 1 COMMENT '状态：1-启用，0-禁用',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- 知识库表
CREATE TABLE t_knowledge_base (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '知识库ID',
    kb_name VARCHAR(100) NOT NULL COMMENT '知识库名称',
    description VARCHAR(500) DEFAULT '' COMMENT '知识库描述',
    creator_id INT NOT NULL COMMENT '创建者ID',
    doc_count INT NOT NULL DEFAULT 0 COMMENT '文档数量',
    status TINYINT NOT NULL DEFAULT 1 COMMENT '状态：1-正常，0-禁用',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (creator_id) REFERENCES t_user(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识库表';

-- 文档表
CREATE TABLE t_document (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '文档ID',
    kb_id INT NOT NULL COMMENT '所属知识库ID',
    file_name VARCHAR(255) NOT NULL COMMENT '文件名',
    file_path VARCHAR(500) NOT NULL COMMENT '文件存储路径',
    file_size BIGINT NOT NULL DEFAULT 0 COMMENT '文件大小（字节）',
    file_type VARCHAR(20) NOT NULL COMMENT '文件类型：txt/pdf/md/docx',
    chunk_count INT NOT NULL DEFAULT 0 COMMENT '分块数量',
    status VARCHAR(20) NOT NULL DEFAULT 'uploading' COMMENT '状态：uploading-上传中，vectorized-已向量化，failed-失败',
    creator_id INT NOT NULL COMMENT '上传者ID',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (kb_id) REFERENCES t_knowledge_base(id),
    FOREIGN KEY (creator_id) REFERENCES t_user(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文档表';

-- 对话历史表
CREATE TABLE t_chat_history (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '记录ID',
    user_id INT NOT NULL COMMENT '用户ID',
    kb_id INT NOT NULL COMMENT '知识库ID',
    session_id VARCHAR(64) NOT NULL COMMENT '会话ID',
    question TEXT NOT NULL COMMENT '用户提问',
    answer TEXT NOT NULL COMMENT 'AI回答',
    source_docs TEXT DEFAULT NULL COMMENT '参考文档来源（JSON格式）',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (user_id) REFERENCES t_user(id),
    FOREIGN KEY (kb_id) REFERENCES t_knowledge_base(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话历史表';

-- WHODrug药物表
CREATE TABLE t_whodrug (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT 'ID',
    mpid VARCHAR(20) DEFAULT NULL COMMENT 'WHODrug MPID',
    drug_code VARCHAR(20) DEFAULT NULL COMMENT 'Drug Code',
    drug_name VARCHAR(500) NOT NULL COMMENT '药物名称',
    atc_code VARCHAR(10) DEFAULT NULL COMMENT 'ATC分类代码',
    pt VARCHAR(100) DEFAULT NULL COMMENT 'WHODrug PT',
    substance_name TEXT DEFAULT NULL COMMENT '活性成分名称',
    strength VARCHAR(200) DEFAULT NULL COMMENT '剂量强度',
    pharmaceutical_form VARCHAR(200) DEFAULT NULL COMMENT '剂型',
    country VARCHAR(120) DEFAULT NULL COMMENT '销售国家',
    mah VARCHAR(500) DEFAULT NULL COMMENT '上市许可持有人',
    language VARCHAR(10) NOT NULL DEFAULT 'en' COMMENT '语言: en/cn',
    source_file VARCHAR(100) DEFAULT NULL COMMENT '来源文件',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '导入时间',
    INDEX idx_mpid (mpid),
    INDEX idx_drug_code (drug_code),
    INDEX idx_language (language),
    INDEX idx_lang_drugname (language, drug_name(80))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='WHODrug药物表';

-- MedDRA术语表
CREATE TABLE t_meddra (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT 'ID',
    code VARCHAR(20) NOT NULL COMMENT 'MedDRA代码',
    name VARCHAR(500) NOT NULL COMMENT '术语名称',
    term_level VARCHAR(10) NOT NULL COMMENT '层级: SOC/HLGT/HLT/PT/LLT',
    parent_code VARCHAR(20) DEFAULT NULL COMMENT '父级代码',
    soc_code VARCHAR(20) DEFAULT NULL COMMENT '系统器官分类代码',
    language VARCHAR(10) NOT NULL DEFAULT 'en' COMMENT '语言: en/cn',
    source_file VARCHAR(100) DEFAULT NULL COMMENT '来源文件',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '导入时间',
    INDEX idx_code (code),
    INDEX idx_level (term_level),
    INDEX idx_language (language),
    INDEX idx_soc (soc_code),
    INDEX idx_lang_level_name (language, term_level, name(50)),
    INDEX idx_lang_level_parent (language, term_level, parent_code),
    INDEX idx_lang_name (language, name(80))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='MedDRA术语表';

-- MedDRA SMQ主表
CREATE TABLE t_meddra_smq (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT 'ID',
    smq_code VARCHAR(20) NOT NULL COMMENT 'SMQ代码',
    smq_name VARCHAR(500) NOT NULL COMMENT 'SMQ名称',
    smq_level VARCHAR(20) DEFAULT '' COMMENT 'SMQ层级',
    description TEXT DEFAULT NULL COMMENT 'SMQ定义描述',
    source_text TEXT DEFAULT NULL COMMENT '参考来源',
    note_text TEXT DEFAULT NULL COMMENT '附注说明',
    meddra_version VARCHAR(20) DEFAULT '' COMMENT 'MedDRA版本',
    status VARCHAR(10) DEFAULT '' COMMENT 'SMQ状态',
    algorithmic_flag VARCHAR(10) DEFAULT '' COMMENT '是否算法型SMQ',
    language VARCHAR(10) NOT NULL DEFAULT 'en' COMMENT '语言: en/cn',
    source_file VARCHAR(100) DEFAULT NULL COMMENT '来源文件',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '导入时间',
    INDEX idx_smq_code (smq_code),
    INDEX idx_smq_language (language)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='MedDRA SMQ主表';

-- MedDRA SMQ术语映射表
CREATE TABLE t_meddra_smq_term (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT 'ID',
    smq_code VARCHAR(20) NOT NULL COMMENT 'SMQ代码',
    term_code VARCHAR(20) NOT NULL COMMENT '术语代码',
    term_name VARCHAR(500) DEFAULT '' COMMENT '术语名称',
    term_level VARCHAR(10) DEFAULT '' COMMENT '术语层级',
    scope VARCHAR(10) DEFAULT '' COMMENT '检索范围',
    category VARCHAR(10) DEFAULT '' COMMENT '类别',
    weight VARCHAR(20) DEFAULT '' COMMENT '权重',
    term_status VARCHAR(10) DEFAULT '' COMMENT '术语状态',
    term_add_version VARCHAR(20) DEFAULT '' COMMENT '术语纳入版本',
    smq_add_version VARCHAR(20) DEFAULT '' COMMENT 'SMQ纳入版本',
    language VARCHAR(10) NOT NULL DEFAULT 'en' COMMENT '语言: en/cn',
    source_file VARCHAR(100) DEFAULT NULL COMMENT '来源文件',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '导入时间',
    INDEX idx_smq_term_smq_code (smq_code),
    INDEX idx_smq_term_code (term_code),
    INDEX idx_smq_term_language (language)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='MedDRA SMQ术语映射表';

-- 数据导入日志表
CREATE TABLE t_import_log (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT 'ID',
    user_id INT DEFAULT NULL COMMENT '操作用户ID',
    dict_type VARCHAR(20) NOT NULL COMMENT '词典类型: whodrug_en/whodrug_cn/meddra_en/meddra_cn',
    file_name VARCHAR(200) DEFAULT NULL COMMENT '导入文件名',
    record_count INT DEFAULT 0 COMMENT '导入记录数',
    status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '状态: pending/running/success/failed',
    error_message TEXT DEFAULT NULL COMMENT '错误信息',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    complete_time DATETIME DEFAULT NULL COMMENT '完成时间',
    FOREIGN KEY (user_id) REFERENCES t_user(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据导入日志表';

-- 插入测试数据
INSERT INTO t_user (username, password, nickname, role, status) VALUES
('admin', 'e10adc3949ba59abbe56e057f20f883e', '管理员', 'admin', 1),
('user1', 'e10adc3949ba59abbe56e057f20f883e', '张三', 'user', 1);

-- 测试知识库
INSERT INTO t_knowledge_base (kb_name, description, creator_id, doc_count, status) VALUES
('WHODrug词典', 'WHODrug全球药物编码词典', 1, 0, 1),
('MedDRA词典', 'MedDRA医学术语词典', 1, 0, 1),
('MedDRA说明文档（中文）', 'MedDRA中文入门指南、SMQ指南和文件格式说明', 1, 0, 1),
('MedDRA说明文档（英文）', 'MedDRA English intro guide, SMQ guide and file format reference', 1, 0, 1);
