"""
数据导入日志模型
对应数据库表 t_import_log
"""
from models import db
from datetime import datetime


class ImportLog(db.Model):
    """数据导入日志表ORM模型"""

    __tablename__ = 't_import_log'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='ID')
    user_id = db.Column(db.Integer, db.ForeignKey('t_user.id'), nullable=True, comment='操作用户ID')
    dict_type = db.Column(db.String(20), nullable=False, comment='词典类型: whodrug_en/whodrug_cn/meddra_en/meddra_cn')
    file_name = db.Column(db.String(200), nullable=True, comment='导入文件名')
    record_count = db.Column(db.Integer, default=0, comment='导入记录数')
    status = db.Column(db.String(20), nullable=False, default='pending', comment='状态: pending/running/success/failed')
    error_message = db.Column(db.Text, nullable=True, comment='错误信息')
    create_time = db.Column(db.DateTime, nullable=False, default=datetime.now, comment='创建时间')
    complete_time = db.Column(db.DateTime, nullable=True, comment='完成时间')

    user = db.relationship('User', backref='import_logs', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else '',
            'dict_type': self.dict_type,
            'file_name': self.file_name or '',
            'record_count': self.record_count,
            'status': self.status,
            'error_message': self.error_message or '',
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S') if self.create_time else '',
            'complete_time': self.complete_time.strftime('%Y-%m-%d %H:%M:%S') if self.complete_time else ''
        }