"""
统计数据路由
提供管理员首页的统计数据接口
"""
from flask import Blueprint
from datetime import datetime, timedelta
from sqlalchemy import func
from models import db
from models.user import User
from models.knowledge_base import KnowledgeBase
from models.document import Document
from models.chat_history import ChatHistory
from models.meddra import MeddraTerm
from models.meddra_smq import MeddraSmq
from models.whodrug import WhodrugDrug
from utils.auth import admin_required
from utils.response import success

# 创建统计蓝图
stats_bp = Blueprint('stats', __name__)


def _visible_kb_query():
    query = KnowledgeBase.query.filter_by(status=1)
    return query.filter(~KnowledgeBase.kb_name.like('MedDRA说明文档%'))


def _all_enabled_doc_query():
    return db.session.query(Document).join(
        KnowledgeBase, Document.kb_id == KnowledgeBase.id
    ).filter(
        KnowledgeBase.status == 1
    )


@stats_bp.route('/overview', methods=['GET'])
@admin_required
def overview():
    """
    获取首页统计概览数据（仅管理员）
    返回: 用户数、知识库数、文档数、今日提问数、近7天趋势、知识库文档占比
    """
    # 基础统计数量
    user_count = User.query.filter_by(status=1).count()
    visible_kbs = _visible_kb_query().all()
    kb_count = len(visible_kbs)

    # 文档总数：t_document 中的用户上传文档
    uploaded_doc_count = _all_enabled_doc_query().count()

    # 词典数据统计（作为"文档资源"纳入总数）
    whodrug_count = db.session.query(func.count(WhodrugDrug.id)).scalar() or 0
    meddra_count = db.session.query(func.count(MeddraTerm.id)).scalar() or 0
    smq_count = db.session.query(func.count(MeddraSmq.id)).scalar() or 0

    # 文档总数 = 用户上传文档 + 词典条目数（以万为单位换算为"文档"不合理，直接用上传文档数）
    # 但如果上传文档为0且有词典数据，展示词典资源数让页面不空
    doc_count = uploaded_doc_count
    has_dict_data = (whodrug_count + meddra_count + smq_count) > 0

    # 今日提问数量
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_chat_count = ChatHistory.query.filter(ChatHistory.create_time >= today_start).count()

    # 近7天每日提问数量趋势
    trend_data = []
    for i in range(6, -1, -1):
        day = datetime.now() - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = ChatHistory.query.filter(
            ChatHistory.create_time >= day_start,
            ChatHistory.create_time < day_end
        ).count()
        trend_data.append({
            'date': day_start.strftime('%m-%d'),
            'count': count
        })

    # 各知识库文档数量占比
    kb_doc_stats = db.session.query(
        KnowledgeBase.kb_name,
        func.count(Document.id).label('doc_count')
    ).join(
        Document, Document.kb_id == KnowledgeBase.id
    ).filter(
        KnowledgeBase.status == 1,
    ).group_by(
        KnowledgeBase.id,
        KnowledgeBase.kb_name
    ).all()

    kb_doc_data = [{'name': name, 'value': count} for name, count in kb_doc_stats]

    # 如果用户上传文档为空但有词典数据，用词典数据填充饼图
    if not kb_doc_data and has_dict_data:
        if whodrug_count > 0:
            kb_doc_data.append({'name': 'WHODrug词典', 'value': whodrug_count})
        if meddra_count > 0:
            kb_doc_data.append({'name': 'MedDRA词典', 'value': meddra_count})
        if smq_count > 0:
            kb_doc_data.append({'name': 'MedDRA SMQ', 'value': smq_count})
        # 同时更新文档总数为词典记录总数
        doc_count = whodrug_count + meddra_count + smq_count

    return success({
        'user_count': user_count,
        'kb_count': kb_count,
        'doc_count': doc_count,
        'today_chat_count': today_chat_count,
        'trend_data': trend_data,
        'kb_doc_data': kb_doc_data
    })
