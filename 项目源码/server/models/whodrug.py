"""
WHODrug 模型
对应数据库表 t_whodrug
"""
from models import db
from datetime import datetime


class WhodrugDrug(db.Model):
    """WHODrug药物表ORM模型"""

    __tablename__ = 't_whodrug'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='ID')
    mpid = db.Column(db.String(20), nullable=True, comment='WHODrug MPID (Medicinal Product Identifier)')
    drug_code = db.Column(db.String(20), nullable=True, comment='Drug Code')
    drug_name = db.Column(db.String(500), nullable=False, comment='药物名称')
    atc_code = db.Column(db.String(10), nullable=True, comment='ATC分类代码')
    pt = db.Column(db.String(100), nullable=True, comment='WHODrug PT')
    substance_name = db.Column(db.Text, nullable=True, comment='活性成分名称')
    strength = db.Column(db.String(200), nullable=True, comment='剂量强度')
    pharmaceutical_form = db.Column(db.String(200), nullable=True, comment='剂型')
    country = db.Column(db.String(120), nullable=True, comment='销售国家')
    mah = db.Column(db.String(500), nullable=True, comment='上市许可持有人')
    language = db.Column(db.String(10), nullable=False, default='en', comment='语言: en/cn')
    source_file = db.Column(db.String(100), nullable=True, comment='来源文件')
    create_time = db.Column(db.DateTime, nullable=False, default=datetime.now, comment='导入时间')

    def to_dict(self):
        return {
            'id': self.id,
            'mpid': self.mpid or '',
            'drug_code': self.drug_code or '',
            'drug_name': self.drug_name,
            'atc_code': self.atc_code or '',
            'pt': self.pt or '',
            'substance_name': self.substance_name or '',
            'strength': self.strength or '',
            'pharmaceutical_form': self.pharmaceutical_form or '',
            'country': self.country or '',
            'mah': self.mah or '',
            'language': self.language,
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S') if self.create_time else ''
        }
