"""
MedDRA SMQ 模型
"""
from datetime import datetime

from models import db


class MeddraSmq(db.Model):
    """SMQ 主表"""

    __tablename__ = 't_meddra_smq'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='ID')
    smq_code = db.Column(db.String(20), nullable=False, comment='SMQ代码')
    smq_name = db.Column(db.String(500), nullable=False, comment='SMQ名称')
    smq_level = db.Column(db.String(20), default='', comment='SMQ层级')
    description = db.Column(db.Text, default=None, comment='SMQ定义描述')
    source_text = db.Column(db.Text, default=None, comment='参考来源')
    note_text = db.Column(db.Text, default=None, comment='附注说明')
    meddra_version = db.Column(db.String(20), default='', comment='MedDRA版本')
    status = db.Column(db.String(10), default='', comment='SMQ状态')
    algorithmic_flag = db.Column(db.String(10), default='', comment='是否算法型SMQ')
    language = db.Column(db.String(10), nullable=False, default='en', comment='语言: en/cn')
    source_file = db.Column(db.String(100), default='', comment='来源文件')
    create_time = db.Column(db.DateTime, nullable=False, default=datetime.now, comment='导入时间')


class MeddraSmqTerm(db.Model):
    """SMQ 术语映射表"""

    __tablename__ = 't_meddra_smq_term'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='ID')
    smq_code = db.Column(db.String(20), nullable=False, comment='SMQ代码')
    term_code = db.Column(db.String(20), nullable=False, comment='术语代码')
    term_name = db.Column(db.String(500), default='', comment='术语名称')
    term_level = db.Column(db.String(10), default='', comment='术语层级')
    scope = db.Column(db.String(10), default='', comment='检索范围')
    category = db.Column(db.String(10), default='', comment='类别')
    weight = db.Column(db.String(20), default='', comment='权重')
    term_status = db.Column(db.String(10), default='', comment='术语状态')
    term_add_version = db.Column(db.String(20), default='', comment='术语纳入版本')
    smq_add_version = db.Column(db.String(20), default='', comment='SMQ纳入版本')
    language = db.Column(db.String(10), nullable=False, default='en', comment='语言: en/cn')
    source_file = db.Column(db.String(100), default='', comment='来源文件')
    create_time = db.Column(db.DateTime, nullable=False, default=datetime.now, comment='导入时间')
