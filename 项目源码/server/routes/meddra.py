"""
MedDRA 术语查询路由
提供术语搜索、层级浏览和语义搜索接口
"""
import re
from flask import Blueprint, request, current_app
from sqlalchemy import func
from models import db
from models.meddra import MeddraTerm
from services.meddra_explain_service import MeddraExplainService
from services.vector_service import VectorService
from utils.auth import login_required
from utils.response import success, error, page_response

meddra_bp = Blueprint('meddra', __name__)
MEDDRA_QUERY_FALLBACK_LEVELS = ['SOC', 'HLGT', 'HLT', 'PT']
MEDDRA_SEMANTIC_LEVEL_SCORES = {
    'PT': 0.99,
    'SOC': 0.93,
    'HLGT': 0.9,
    'HLT': 0.88,
}


def _get_term_by_code(code, language):
    if not code:
        return None
    return MeddraTerm.query.filter_by(code=code, language=language).first()


def _build_term_chain(term, language):
    llt_code = ''
    llt_name = ''
    pt_code = ''
    pt_name = ''
    hlt_code = ''
    hlt_name = ''

    level = term.term_level
    if level == 'LLT':
        llt_code = term.code
        llt_name = term.name
        pt_term = _get_term_by_code(term.parent_code, language)
        if pt_term:
            pt_code = pt_term.code
            pt_name = pt_term.name
            hlt_term = _get_term_by_code(pt_term.parent_code, language)
            if hlt_term:
                hlt_code = hlt_term.code
                hlt_name = hlt_term.name
    elif level == 'PT':
        pt_code = term.code
        pt_name = term.name
        hlt_term = _get_term_by_code(term.parent_code, language)
        if hlt_term:
            hlt_code = hlt_term.code
            hlt_name = hlt_term.name
    elif level == 'HLT':
        hlt_code = term.code
        hlt_name = term.name

    return {
        'llt_code': llt_code,
        'llt_name': llt_name,
        'pt_code': pt_code,
        'pt_name': pt_name,
        'hlt_code': hlt_code,
        'hlt_name': hlt_name
    }


def _serialize_term(term):
    data = term.to_dict()
    data.update(_build_term_chain(term, term.language))
    return data


def _tokenize_query(keyword):
    tokens = re.split(r'[\s,，。;；:：/\\()（）]+', keyword or '')
    tokens = [token.strip() for token in tokens if len(token.strip()) >= 2]
    return [keyword.strip()] + tokens if keyword and keyword.strip() else tokens


def _build_keyword_conditions(keyword):
    conditions = []
    for token in _tokenize_query(keyword):
        pattern = f'%{token}%'
        conditions.append(MeddraTerm.name.like(pattern))
        conditions.append(MeddraTerm.code.like(pattern))
    return conditions


def _term_match_rank(term, keyword):
    normalized = (keyword or '').strip().lower()
    name = (term.name or '').lower()
    code = (term.code or '').lower()
    if normalized and (name == normalized or code == normalized):
        return 0
    if normalized and (name.startswith(normalized) or code.startswith(normalized)):
        return 1
    if normalized and normalized in name:
        return 2
    return 3


def _ordered_terms_for_query(keyword, language, levels):
    conditions = _build_keyword_conditions(keyword)
    if not conditions:
        return []

    rows = []
    seen_codes = set()
    for level in levels:
        level_rows = MeddraTerm.query.filter(
            MeddraTerm.language == language,
            MeddraTerm.term_level == level,
            db.or_(*conditions)
        ).all()
        level_rows.sort(key=lambda item: (_term_match_rank(item, keyword), item.name))
        for row in level_rows:
            if row.code in seen_codes:
                continue
            seen_codes.add(row.code)
            rows.append(row)
    return rows


def _search_terms_pt_first(keyword, language):
    pt_rows = _ordered_terms_for_query(keyword, language, ['PT'])
    if pt_rows:
        return pt_rows
    return _ordered_terms_for_query(keyword, language, MEDDRA_QUERY_FALLBACK_LEVELS)


def _serialize_ranked_term(term, score):
    data = _serialize_term(term)
    data.update({
        'level': term.term_level,
        'score': score,
    })
    return data


@meddra_bp.route('/search', methods=['GET'])
@login_required
def search():
    """
    MedDRA 术语搜索（数据库模糊搜索）
    查询参数: keyword, language, level, page, page_size
    """
    keyword = request.args.get('keyword', '').strip()
    language = request.args.get('language', 'cn')
    level = request.args.get('level', '')
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', request.args.get('pageSize', 20), type=int)

    if keyword and not level:
        rows = _search_terms_pt_first(keyword, language)
        total = len(rows)
        start = max(0, (page - 1) * page_size)
        end = start + page_size
        items = [_serialize_term(item) for item in rows[start:end]]
        return page_response(items, total, page, page_size)

    query = MeddraTerm.query.filter_by(language=language)

    if keyword:
        query = query.filter(db.or_(*_build_keyword_conditions(keyword)))

    if level:
        query = query.filter_by(term_level=level)

    query = query.order_by(MeddraTerm.name)
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)

    items = [_serialize_term(item) for item in pagination.items]
    return page_response(items, pagination.total, page, page_size)


@meddra_bp.route('/semantic_search', methods=['POST'])
@login_required
def semantic_search():
    """
    MedDRA 语义搜索（向量检索）
    请求参数: term(搜索词), language, top_k
    返回: 相似术语列表及匹配分数
    """
    data = request.get_json()
    if not data:
        return error('请提供搜索词')

    term = data.get('term', '').strip()
    language = data.get('language', 'cn')
    top_k = data.get('top_k', 10)

    if not term:
        return error('搜索词不能为空')

    try:
        direct_rows = _search_terms_pt_first(term, language)
        if direct_rows:
            results = []
            for row in direct_rows[:top_k]:
                base_score = MEDDRA_SEMANTIC_LEVEL_SCORES.get(row.term_level, 0.85)
                rank_bonus = max(0, 0.02 - _term_match_rank(row, term) * 0.01)
                results.append(_serialize_ranked_term(row, min(1, base_score + rank_bonus)))
            return success(results)

        docs = VectorService().search_collection(f'meddra_{language}', term, top_k=top_k)

        results = []
        for doc, score in docs:
            level = doc.metadata.get('level', '')
            code = doc.metadata.get('code', '')
            matched_term = MeddraTerm.query.filter_by(code=code, language=language).first()
            chain = _build_term_chain(matched_term, language) if matched_term else {
                'llt_code': '',
                'llt_name': '',
                'pt_code': '',
                'pt_name': '',
                'hlt_code': '',
                'hlt_name': ''
            }
            results.append({
                'code': code,
                'name': doc.metadata.get('name', doc.page_content),
                'level': level,
                'score': max(0, 1 - float(score)),
                **chain
            })

        return success(results)
    except Exception as e:
        current_app.logger.error(f'语义搜索失败: {e}', exc_info=True)
        return error('语义搜索失败，请稍后重试')


@meddra_bp.route('/explain_batch', methods=['POST'])
@login_required
def explain_batch():
    """
    MedDRA 小批量解释验证
    请求参数:
      - terms: 术语数组（最多小批量）
      - language: cn/en，可选
      - threshold: 评分阈值，可选，默认 80
    """
    data = request.get_json()
    if not data:
        return error('请提供待验证术语')

    terms = data.get('terms') or []
    if isinstance(terms, str):
        terms = [terms]

    terms = [str(term or '').strip() for term in terms if str(term or '').strip()]
    if not terms:
        return error('至少需要提供一个术语')

    language = data.get('language', 'cn')
    threshold = data.get('threshold')
    max_iterations = data.get('max_iterations')

    try:
        service = MeddraExplainService()
        result = service.explain_batch(
            terms,
            language=language,
            threshold=threshold,
            max_iterations=max_iterations
        )
        return success(result)
    except Exception as e:
        current_app.logger.error(f'批量解释验证失败: {e}', exc_info=True)
        return error('批量解释验证失败，请稍后重试')


@meddra_bp.route('/hierarchy', methods=['GET'])
@login_required
def hierarchy():
    """
    获取 MedDRA 层级结构
    查询参数: language
    一次性加载所有层级数据，在内存中组装树结构，避免 N+1 查询
    """
    language = request.args.get('language', 'cn')

    # 一次性查出所有层级的术语
    all_terms = MeddraTerm.query.filter_by(language=language).filter(
        MeddraTerm.term_level.in_(['SOC', 'HLGT', 'HLT', 'PT'])
    ).all()

    # 按层级分组
    soc_map = {}
    hlgt_map = {}
    hlt_map = {}
    pt_by_parent = {}  # parent_code -> [pt, ...]
    hlt_by_parent = {}  # parent_code(hlgt) -> [hlt, ...]
    hlgt_by_soc = {}  # soc_code -> [hlgt, ...]

    for term in all_terms:
        if term.term_level == 'SOC':
            soc_map[term.code] = term
        elif term.term_level == 'HLGT':
            hlgt_map[term.code] = term
            hlgt_by_soc.setdefault(term.soc_code, []).append(term)
        elif term.term_level == 'HLT':
            hlt_map[term.code] = term
            hlt_by_parent.setdefault(term.parent_code, []).append(term)
        elif term.term_level == 'PT':
            pt_by_parent.setdefault(term.parent_code, []).append(term)

    # 组装树结构
    result = []
    for soc_code in sorted(soc_map.keys(), key=lambda c: soc_map[c].name):
        soc = soc_map[soc_code]
        hlgt_list = []
        for hlgt in sorted(hlgt_by_soc.get(soc_code, []), key=lambda t: t.name):
            hlt_list = []
            for hlt in sorted(hlt_by_parent.get(hlgt.code, []), key=lambda t: t.name):
                pts = sorted(pt_by_parent.get(hlt.code, []), key=lambda t: t.name)[:50]
                pt_list = [{'code': pt.code, 'name': pt.name} for pt in pts]
                hlt_list.append({
                    'code': hlt.code,
                    'name': hlt.name,
                    'pts': pt_list
                })
            hlgt_list.append({
                'code': hlgt.code,
                'name': hlgt.name,
                'hlts': hlt_list
            })
        result.append({
            'code': soc.code,
            'name': soc.name,
            'hlgts': hlgt_list
        })

    return success(result)


@meddra_bp.route('/browse', methods=['GET'])
@login_required
def browse():
    """
    按层级浏览 MedDRA 术语
    查询参数: level(SOC/HLGT/HLT/PT/LLT), parent_code, language, page, page_size
    """
    level = request.args.get('level', 'SOC')
    parent_code = request.args.get('parent_code', '')
    language = request.args.get('language', 'cn')
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 50, type=int)

    query = MeddraTerm.query.filter_by(language=language, term_level=level)

    if level != 'SOC' and parent_code:
        query = query.filter_by(parent_code=parent_code)

    if level == 'SOC':
        query = query.filter_by(soc_code=MeddraTerm.code)

    query = query.order_by(MeddraTerm.name)
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)

    items = [item.to_dict() for item in pagination.items]
    return page_response(items, pagination.total, page, page_size)


@meddra_bp.route('/stats', methods=['GET'])
@login_required
def stats():
    """
    获取 MedDRA 统计信息
    """
    en_count = db.session.query(func.count(MeddraTerm.id)).filter_by(language='en').scalar()
    cn_count = db.session.query(func.count(MeddraTerm.id)).filter_by(language='cn').scalar()

    level_stats = {}
    for lang in ['en', 'cn']:
        for level in ['SOC', 'HLGT', 'HLT', 'PT', 'LLT']:
            count = db.session.query(func.count(MeddraTerm.id)).filter_by(
                language=lang, term_level=level
            ).scalar()
            key = f'{lang}_{level}'
            level_stats[key] = count

    return success({
        'total': en_count + cn_count,
        'english': en_count,
        'chinese': cn_count,
        'level_stats': level_stats
    })
