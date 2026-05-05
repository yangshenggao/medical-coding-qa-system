/*
SQLyog Community v13.2.0 (64 bit)
MySQL - 8.1.0 : Database - db_qa
*********************************************************************
*/

/*!40101 SET NAMES utf8 */;

/*!40101 SET SQL_MODE=''*/;

/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
CREATE DATABASE /*!32312 IF NOT EXISTS*/`db_qa` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;

USE `db_qa`;

/*Table structure for table `t_chat_history` */

DROP TABLE IF EXISTS `t_chat_history`;

CREATE TABLE `t_chat_history` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '记录ID',
  `user_id` int NOT NULL COMMENT '用户ID',
  `kb_id` int NOT NULL COMMENT '知识库ID',
  `session_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '会话ID',
  `question` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '用户提问',
  `answer` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'AI回答',
  `source_docs` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '参考文档来源（JSON格式）',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `kb_id` (`kb_id`),
  CONSTRAINT `t_chat_history_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `t_user` (`id`),
  CONSTRAINT `t_chat_history_ibfk_2` FOREIGN KEY (`kb_id`) REFERENCES `t_knowledge_base` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=42 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话历史表';

/*Data for the table `t_chat_history` */

insert  into `t_chat_history`(`id`,`user_id`,`kb_id`,`session_id`,`question`,`answer`,`source_docs`,`create_time`) values 
(37,1,3,'sess_mniiqjk21gzjp0','推荐下类风湿关节炎的中药药方','根据参考资料，针对类风湿关节炎推荐的中药药方为：\n\n**国医大师朱良春——益肾蠲痹方**\n\n**组成**：熟地20g、鹿角片10g（先煎）、全蝎6g、蜈蚣2条、地龙12g、僵蚕10g、乌梢蛇15g、黄芪30g、当归12g、鸡血藤30g、威灵仙15g、甘草6g\n\n**方义**：本方以补肾填精、温阳强骨为君，全蝎、蜈蚣搜风通络解痉止痛为臣，地龙、僵蚕、乌梢蛇祛风通络为佐，黄芪、当归益气养血扶正，鸡血藤活血通络、威灵仙祛风湿通经络，甘草调和诸药为使。\n\n**临床应用**：朱老认为类风湿关节炎的根本病机为\"肾虚督亏、寒湿瘀阻\"，治当补肾壮督为本、祛风除湿通络为标。虫类药物性善走窜，对久痹入络的顽症有独特疗效，适用于类风湿关节炎属肾虚督亏、寒湿瘀阻证的患者。','[{\"file_name\": \"12378559c8d94adba37564603f635100.pdf\", \"content\": \"g、当归12g、鸡血藤30g、威灵仙15g、甘草6g。\\n   \\n方义分析：熟地、鹿角片补肾填精、温阳强骨（君）；全蝎、蜈蚣搜风通络、解痉止痛（臣）；地龙、僵蚕、\\n乌梢蛇祛风通络（佐）；黄芪、当归益气养血扶正（佐）；鸡血藤活血通络、威灵仙祛风湿通经络（佐）；甘\\n草调和诸药（使）。\\n   \\n临床经验：朱老认为类风湿关节炎的根本病机为\\\"肾虚督亏、寒湿瘀阻\\\"，治当补肾壮督为本、祛风除湿通络为\\n标。虫类药物\"}]','2026-04-03 14:27:30'),
(38,1,1,'sess_mniix8ud0bb4we','推荐下感冒的中药药方','根据参考资料，感冒在中医中分为风寒感冒、风热感冒和暑湿感冒三型，每种类型对应不同的中药药方推荐如下：\n\n1. **风寒感冒**：代表方为**荆防败毒散或麻黄汤加减**。适用于恶寒重、发热轻、无汗、头痛身痛、鼻塞流清涕等症状。\n\n2. **风热感冒**：代表方为**银翘散或桑菊饮加减**。适用于发热重、恶寒轻、有汗或少汗、头痛、咽喉肿痛、鼻塞流黄涕等症状。\n\n3. **暑湿感冒**：代表方为**新加香薷饮合六一散**。多见于夏季，适用于发热、恶寒、头痛头重、身重倦怠、胸闷脘痞等症状。\n\n以上药方信息均来源于企业内部知识库参考资料，供临床参考使用。','[{\"file_name\": \"81b2f4ddc52f4d548cb2416d017e8d2e.pdf\", \"content\": \"常见病证中医诊疗方案\\n一、感冒\\n   \\n感冒是由外感风邪引起的以鼻塞、流涕、喷嚏、头痛、恶寒、发热、全身不适等为主要表现的外感疾病。中医\\n将感冒分为风寒感冒、风热感冒和暑湿感冒三型。\\n    1.\\n风寒感冒：症见恶寒重、发热轻、无汗、头痛身痛、鼻塞流清涕、咳嗽痰白稀、口不渴或渴喜热饮。舌苔薄白\\n，脉浮紧。治法：辛温解表。代表方：荆防败毒散或麻黄汤加减。常用药物：麻黄、桂枝、荆芥、防风、羌活\\n、白芷\"}]','2026-04-03 14:32:46'),
(39,1,2,'sess_mnikssll79inij','六味地黄丸有哪些功效？','根据参考资料，六味地黄丸的功效是滋补肝肾。其主治肝肾阴虚证，具体症状包括腰膝酸软、头晕目眩、耳鸣耳聋、盗汗遗精、骨蒸潮热、手足心热、口燥咽干。舌红少苔，脉沉细数。该方由熟地黄、山茱萸、山药、泽泻、牡丹皮、茯苓六味药物组成，具有\"三补三泻\"的特点，以补为主，补中寓泻，能滋补肝脾肾三阴。','[{\"file_name\": \"890373f5f6fc477eb0ac91b3f96d3851.pdf\", \"content\": \"作痛。舌淡苔白，脉细弦或细涩。\\n   \\n方解：熟地黄滋阴补血、填精益髓（君）；当归补血活血、调经（臣）；白芍养血敛阴、和营（佐）；川芎活\\n血行气、畅通气血（使）。全方补血而不滞血，行血而不伤血，补中有通，通中有补。\\n   \\n现代应用：常用于月经不调、痛经、闭经、胎产诸疾以及各种贫血。现代研究表明四物汤能促进造血功能、改\\n善微循环、调节内分泌功能。加减应用广泛：兼气虚加黄芪、党参成为八珍汤组合之一。\"}, {\"file_name\": \"72a9eda063054fcbaf66d7c7793ad82d.txt\", \"content\": \"三、阴虚类证型\\n----------------------------------------\\n    1. 肺阴虚证：干咳少痰或痰中带血丝、口咽干燥、声音嘶哑、午后潮热、盗汗。舌红少苔，脉细数。治法：滋阴润肺。代表方：百合固金汤。\\n    2. 胃阴虚证：胃脘灼痛隐痛、饥不欲食、口干舌燥、干呕呃逆、大便干结。舌红少苔，脉细数。治法：养阴益胃。代表方：益胃汤。\\n    3. 肝阴虚证：头晕耳鸣、\"}]','2026-04-03 15:25:13'),
(40,1,1,'sess_mnimwxtm7kua86','推荐下感冒的中药药方','根据中医诊疗方案，感冒在中医中分为风寒感冒、风热感冒和暑湿感冒三种类型，每种类型对应不同的中药药方推荐如下：\n\n1. **风寒感冒**：代表方为**荆防败毒散或麻黄汤加减**。适用症状：恶寒重、发热轻、无汗、头痛身痛、鼻塞流清涕、咳嗽痰白稀、口不渴或渴喜热饮。\n\n2. **风热感冒**：代表方为**银翘散或桑菊饮加减**。适用症状：发热重、恶寒轻、有汗或少汗、头胀痛、咽喉肿痛、鼻塞流黄涕、咳嗽痰黄粘、口渴欲饮。\n\n3. **暑湿感冒**：代表方为**新加香薷饮合六一散**。适用症状：多见于夏季，发热、恶寒、头痛头重、身重倦怠、胸闷脘痞、恶心呕吐、腹泻。\n\n以上药方均基于常见病证中医诊疗方案中的标准推荐，具体使用需结合患者实际症状辨证施治。','[{\"file_name\": \"81b2f4ddc52f4d548cb2416d017e8d2e.pdf\", \"content\": \"常见病证中医诊疗方案\\n一、感冒\\n   \\n感冒是由外感风邪引起的以鼻塞、流涕、喷嚏、头痛、恶寒、发热、全身不适等为主要表现的外感疾病。中医\\n将感冒分为风寒感冒、风热感冒和暑湿感冒三型。\\n    1.\\n风寒感冒：症见恶寒重、发热轻、无汗、头痛身痛、鼻塞流清涕、咳嗽痰白稀、口不渴或渴喜热饮。舌苔薄白\\n，脉浮紧。治法：辛温解表。代表方：荆防败毒散或麻黄汤加减。常用药物：麻黄、桂枝、荆芥、防风、羌活\\n、白芷\"}]','2026-04-03 16:24:10'),
(41,2,1,'sess_mnin2ig1vp6oas','推荐下类风湿关节炎的中药药方','根据您提供的参考资料，我仔细检查了所有内容，但参考资料中没有关于类风湿关节炎的中药药方信息。\n\n参考资料主要包含头痛、失眠、咳嗽和感冒等常见症状的中医辨证施治内容，没有涉及类风湿关节炎的相关方剂。\n\n因此，我无法根据提供的参考资料为您推荐类风湿关节炎的中药药方。如果您需要类风湿关节炎的中医治疗方案，建议咨询专业中医师获取针对性的诊疗建议。','[{\"file_name\": \"81b2f4ddc52f4d548cb2416d017e8d2e.pdf\", \"content\": \"2.\\n风热头痛：头痛而胀，甚则头痛如裂，发热恶风，面红目赤。苔黄，脉浮数。治法：疏风清热和络。方用芎芷\\n石膏汤。\\n    3.\\n肝阳上亢头痛：头痛眩晕，心烦易怒，夜寐不宁，面红口苦。舌红苔黄，脉弦有力。治法：平肝潜阳息风。方\\n用天麻钩藤饮。\\n    4.\\n瘀血头痛：头痛经久不愈，痛处固定不移，痛如锥刺。舌紫暗或有瘀斑，脉细涩。治法：活血化瘀、通窍止痛\\n。方用通窍活血汤。\\n四、失眠\\n   \\n失眠又称\"}]','2026-04-03 16:26:53');

/*Table structure for table `t_document` */

DROP TABLE IF EXISTS `t_document`;

CREATE TABLE `t_document` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '文档ID',
  `kb_id` int NOT NULL COMMENT '所属知识库ID',
  `file_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件名',
  `file_path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件存储路径',
  `file_size` bigint NOT NULL DEFAULT '0' COMMENT '文件大小（字节）',
  `file_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件类型：txt/pdf/md/docx',
  `chunk_count` int NOT NULL DEFAULT '0' COMMENT '分块数量',
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'uploading' COMMENT '状态：uploading-上传中，vectorized-已向量化，failed-失败',
  `creator_id` int NOT NULL COMMENT '上传者ID',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `kb_id` (`kb_id`),
  KEY `creator_id` (`creator_id`),
  CONSTRAINT `t_document_ibfk_1` FOREIGN KEY (`kb_id`) REFERENCES `t_knowledge_base` (`id`),
  CONSTRAINT `t_document_ibfk_2` FOREIGN KEY (`creator_id`) REFERENCES `t_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=61 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文档表';

/*Data for the table `t_document` */

insert  into `t_document`(`id`,`kb_id`,`file_name`,`file_path`,`file_size`,`file_type`,`chunk_count`,`status`,`creator_id`,`create_time`) values 
(49,1,'常见病证中医诊疗方案.pdf','D:\\sys\\server\\uploads\\81b2f4ddc52f4d548cb2416d017e8d2e.pdf',64383,'pdf',4,'vectorized',1,'2026-04-03 13:54:31'),
(50,1,'中医脉象诊断知识.txt','D:\\sys\\server\\uploads\\3bdbee5c905e4fec9ba48da2c335e8ca.txt',3739,'txt',4,'vectorized',1,'2026-04-03 13:55:52'),
(51,1,'中医四诊合参临床指南.docx','D:\\sys\\server\\uploads\\51b165ba9f2d41f3bff159b5bcccab8e.docx',40194,'docx',5,'vectorized',1,'2026-04-03 13:56:23'),
(52,1,'中医体质辨识标准.md','D:\\sys\\server\\uploads\\7eefa84c5eb34120952320fc71a0c222.md',5995,'md',5,'vectorized',1,'2026-04-03 13:57:00'),
(53,2,'经典名方与现代应用.pdf','D:\\sys\\server\\uploads\\890373f5f6fc477eb0ac91b3f96d3851.pdf',64823,'pdf',4,'vectorized',1,'2026-04-03 14:00:10'),
(54,2,'中药方剂配伍指南.md','D:\\sys\\server\\uploads\\4cc9bb7f78744d699955b97fba41efb1.md',3938,'md',3,'vectorized',1,'2026-04-03 14:00:45'),
(55,2,'中医辨证论治方法体系.docx','D:\\sys\\server\\uploads\\ddd7b0a3214b4407baffffb38b5d66e5.docx',39730,'docx',5,'vectorized',1,'2026-04-03 14:01:22'),
(56,2,'中医证型分类标准.txt','D:\\sys\\server\\uploads\\72a9eda063054fcbaf66d7c7793ad82d.txt',4155,'txt',5,'vectorized',1,'2026-04-03 14:02:21'),
(57,3,'历代中医经典理论溯源.docx','D:\\sys\\server\\uploads\\f167ab8276e34598a42f098ace9ae8a0.docx',39710,'docx',4,'vectorized',1,'2026-04-03 14:03:01'),
(58,3,'名老中医经验方集萃.pdf','D:\\sys\\server\\uploads\\12378559c8d94adba37564603f635100.pdf',63750,'pdf',4,'vectorized',1,'2026-04-03 14:03:37'),
(59,3,'中医药典籍核心条文.txt','D:\\sys\\server\\uploads\\4317cb18960441778ddeff0bb7d293ec.txt',5446,'txt',6,'vectorized',1,'2026-04-03 14:04:27'),
(60,3,'中医诊疗技术传承脉络.md','D:\\sys\\server\\uploads\\2c5b6277ca6b4de78f95d3abd87fb377.md',4659,'md',4,'vectorized',1,'2026-04-03 14:05:46');

/*Table structure for table `t_knowledge_base` */

DROP TABLE IF EXISTS `t_knowledge_base`;

CREATE TABLE `t_knowledge_base` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '知识库ID',
  `kb_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '知识库名称',
  `description` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '知识库描述',
  `creator_id` int NOT NULL COMMENT '创建者ID',
  `doc_count` int NOT NULL DEFAULT '0' COMMENT '文档数量',
  `status` tinyint NOT NULL DEFAULT '1' COMMENT '状态：1-正常，0-禁用',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `creator_id` (`creator_id`),
  CONSTRAINT `t_knowledge_base_ibfk_1` FOREIGN KEY (`creator_id`) REFERENCES `t_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识库表';

/*Data for the table `t_knowledge_base` */

insert  into `t_knowledge_base`(`id`,`kb_name`,`description`,`creator_id`,`doc_count`,`status`,`create_time`,`update_time`) values 
(1,'中医临床智诊核心知识库','包含中医临床智诊核心知识库等文档',1,4,1,'2026-03-21 18:20:17','2026-04-03 13:57:28'),
(2,'中医药智能辨证诊疗知识库','包含中医药智能辨证诊疗知识库信息等',1,4,1,'2026-03-21 18:20:17','2026-04-03 14:02:43'),
(3,'国医临床智能诊疗溯源知识库','包含国医临床智能诊疗溯源知识库信息等',1,4,1,'2026-03-21 18:20:17','2026-04-03 14:06:09');

/*Table structure for table `t_user` */

DROP TABLE IF EXISTS `t_user`;

CREATE TABLE `t_user` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `username` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '用户名',
  `password` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '密码（MD5加密）',
  `nickname` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '昵称',
  `role` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'user' COMMENT '角色：admin-管理员，user-普通用户',
  `avatar` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '头像地址',
  `status` tinyint NOT NULL DEFAULT '1' COMMENT '状态：1-启用，0-禁用',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

/*Data for the table `t_user` */

insert  into `t_user`(`id`,`username`,`password`,`nickname`,`role`,`avatar`,`status`,`create_time`,`update_time`) values 
(1,'kyson','e10adc3949ba59abbe56e057f20f883e','kyson','admin','',1,'2026-03-21 18:20:17','2026-03-24 11:26:20'),
(2,'user1','e10adc3949ba59abbe56e057f20f883e','张三','user','',1,'2026-03-21 18:20:17','2026-03-21 18:20:17'),
(3,'user2','e10adc3949ba59abbe56e057f20f883e','李四','user','',1,'2026-03-21 18:20:17','2026-03-21 18:20:17');

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;
