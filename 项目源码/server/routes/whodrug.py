"""
WHODrug 编码查询路由
提供药物编码搜索和详情查询接口
"""
from flask import Blueprint, request, g
from models import db
from models.whodrug import WhodrugDrug
from utils.auth import login_required
from utils.response import success, error, page_response

whodrug_bp = Blueprint('whodrug', __name__)


@whodrug_bp.route('/search', methods=['GET'])
@login_required
def search():
    """
    WHODrug 药物搜索
    查询参数: keyword(关键词), language(语言: en/cn), page, page_size
    """
    keyword = request.args.get('keyword', '').strip()
    language = request.args.get('language', 'cn')
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)

    query = WhodrugDrug.query.filter_by(language=language)

    if keyword:
        keyword_pattern = f'%{keyword}%'
        query = query.filter(
            db.or_(
                WhodrugDrug.drug_name.like(keyword_pattern),
                WhodrugDrug.substance_name.like(keyword_pattern),
                WhodrugDrug.mpid.like(keyword_pattern),
                WhodrugDrug.drug_code.like(keyword_pattern),
                WhodrugDrug.atc_code.like(keyword_pattern)
            )
        )

    query = query.order_by(WhodrugDrug.drug_name)
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)

    items = [item.to_dict() for item in pagination.items]
    return page_response(items, pagination.total, page, page_size)


@whodrug_bp.route('/detail/<mpid>', methods=['GET'])
@login_required
def detail(mpid):
    """
    获取 WHODrug 药物详情
    路径参数: mpid (MPID或Drug Code)
    """
    lang = request.args.get('language', 'cn')
    
    drug = WhodrugDrug.query.filter(
        db.or_(
            WhodrugDrug.mpid == mpid,
            WhodrugDrug.drug_code == mpid
        ),
        WhodrugDrug.language == lang
    ).first()

    if not drug:
        return error('未找到该药物', 404)

    return success(drug.to_dict())


@whodrug_bp.route('/stats', methods=['GET'])
@login_required
def stats():
    """
    获取 WHODrug 统计信息
    """
    from sqlalchemy import func
    
    en_count = db.session.query(func.count(WhodrugDrug.id)).filter_by(language='en').scalar()
    cn_count = db.session.query(func.count(WhodrugDrug.id)).filter_by(language='cn').scalar()
    
    return success({
        'total': en_count + cn_count,
        'english': en_count,
        'chinese': cn_count
    })