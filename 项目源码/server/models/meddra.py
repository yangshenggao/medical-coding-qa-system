"""
MedDRA 模型
对应数据库表 t_meddra
"""
from models import db
from datetime import datetime


class MeddraTerm(db.Model):
    """MedDRA术语表ORM模型"""

    __tablename__ = 't_meddra'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='ID')
    code = db.Column(db.String(20), nullable=False, comment='MedDRA代码')
    name = db.Column(db.String(500), nullable=False, comment='术语名称')
    term_level = db.Column(db.String(10), nullable=False, comment='层级: SOC/HLGT/HLT/PT/LLT')
    parent_code = db.Column(db.String(20), nullable=True, comment='父级代码')
    soc_code = db.Column(db.String(20), nullable=True, comment='系统器官分类代码')
    language = db.Column(db.String(10), nullable=False, default='en', comment='语言: en/cn')
    source_file = db.Column(db.String(100), nullable=True, comment='来源文件')
    create_time = db.Column(db.DateTime, nullable=False, default=datetime.now, comment='导入时间')

    __table_args__ = (
        db.Index('idx_code', 'code'),
        db.Index('idx_level', 'term_level'),
        db.Index('idx_language', 'language'),
        db.Index('idx_soc', 'soc_code'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'term_level': self.term_level,
            'parent_code': self.parent_code or '',
            'soc_code': self.soc_code or '',
            'language': self.language,
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S') if self.create_time else ''
        }