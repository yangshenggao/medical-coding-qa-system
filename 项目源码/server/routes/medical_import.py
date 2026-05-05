"""
医学词典数据导入路由
提供 WHODrug 和 MedDRA 数据导入接口
"""
import csv
import os
import threading
from datetime import datetime

from flask import Blueprint, g, request
from sqlalchemy import func

from models import db
from models.import_log import ImportLog
from models.meddra import MeddraTerm
from models.meddra_smq import MeddraSmq, MeddraSmqTerm
from models.whodrug import WhodrugDrug
from services.vector_service import OllamaServiceError, VectorService
from utils.auth import admin_required
from utils.response import error, page_response, success

# 导入并发锁，防止同一类型重复导入
_import_locks = {}
_locks_guard = threading.Lock()


def _acquire_import_lock(dict_type):
    """尝试获取指定词典类型的导入锁，返回是否成功"""
    with _locks_guard:
        if dict_type in _import_locks:
            return False
        _import_locks[dict_type] = True
        return True


def _release_import_lock(dict_type):
    """释放指定词典类型的导入锁"""
    with _locks_guard:
        _import_locks.pop(dict_type, None)

medical_import_bp = Blueprint('medical_import', __name__)

CURRENT_FILE = os.path.abspath(__file__)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_FILE))))
MEDDRA_LEVEL_NUM_MAP = {
    '1': 'SOC',
    '2': 'HLGT',
    '3': 'HLT',
    '4': 'PT',
    '5': 'LLT',
}


def _resolve_dict_path():
    env_path = os.environ.get('MEDICAL_DICT_DIR')
    candidates = [env_path]

    cursor = os.path.dirname(CURRENT_FILE)
    for _ in range(8):
        candidates.append(os.path.join(cursor, '知识库文件'))
        parent = os.path.dirname(cursor)
        if parent == cursor:
            break
        cursor = parent

    candidates.extend([
        os.path.join(PROJECT_ROOT, '知识库文件'),
        os.path.join(os.getcwd(), '知识库文件'),
        os.path.join(os.path.dirname(PROJECT_ROOT), '知识库文件'),
    ])

    for path in candidates:
        if path and os.path.exists(path):
            return os.path.abspath(path)

    return os.path.abspath(os.path.join(PROJECT_ROOT, '知识库文件'))


DICT_PATH = _resolve_dict_path()


def _clean_text(value):
    return (value or '').strip()


def _limit_text(value, max_len):
    return _clean_text(value)[:max_len]


def _build_whodrug_key(*parts):
    cleaned = [_clean_text(part) for part in parts]
    if not all(cleaned):
        return ''
    return '-'.join(cleaned)


def _read_csv_rows(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore', newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            if row:
                yield row


def _read_pipe_rows(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.rstrip('\n\r')
            if not line:
                continue
            yield line.split('$')


def _get_whodrug_folder(language):
    folder_name = 'WHODrug Global 2026 Mar 1' if language == 'en' else 'WHODrug Global Chinese 2026 Mar 1'
    folder_path = os.path.join(DICT_PATH, folder_name)
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f'未找到目录: {folder_path}')
    return folder_path


def _get_meddra_folder(language):
    folder_name = 'English_29_0' if language == 'en' else 'Chinese_29_0'
    ascii_folder = 'MedAscii' if language == 'en' else 'ascii-290'
    folder_path = os.path.join(DICT_PATH, folder_name, ascii_folder)
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f'未找到目录: {folder_path}')
    return folder_path


def _get_meddra_release_folder(language):
    folder_name = 'English_29_0' if language == 'en' else 'Chinese_29_0'
    folder_path = os.path.join(DICT_PATH, folder_name)
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f'未找到目录: {folder_path}')
    return folder_path


def _load_meddra_name_maps(folder_path):
    levels = [
        ('SOC', 'soc.asc'),
        ('HLGT', 'hlgt.asc'),
        ('HLT', 'hlt.asc'),
        ('PT', 'pt.asc'),
        ('LLT', 'llt.asc'),
    ]

    name_maps = {}
    for level, filename in levels:
        level_map = {}
        for row in _read_pipe_rows(os.path.join(folder_path, filename)):
            if len(row) >= 2:
                code = _clean_text(row[0])
                name = _clean_text(row[1])
                if code and name:
                    level_map[code] = {
                        'name': name,
                        'row': row
                    }
        name_maps[level] = level_map
    return name_maps


def _lookup_meddra_term(name_maps, code, level_hint=''):
    if not code:
        return '', level_hint

    if level_hint:
        item = name_maps.get(level_hint, {}).get(code)
        if item:
            return item['name'], level_hint

    for level, level_map in name_maps.items():
        item = level_map.get(code)
        if item:
            return item['name'], level
    return '', level_hint


def _build_whodrug_records(language):
    folder_path = _get_whodrug_folder(language)
    b3_dir = os.path.join(folder_path, 'whodrug_global_b3_mar_1_2026')
    c3_dir = os.path.join(folder_path, 'whodrug_global_c3_mar_1_2026')

    dd_path = os.path.join(b3_dir, 'DD.csv')
    dda_path = os.path.join(b3_dir, 'DDA.csv')
    ing_path = os.path.join(b3_dir, 'ING.csv')
    bna_path = os.path.join(b3_dir, 'BNA.csv')
    mp_path = os.path.join(c3_dir, 'MP.csv')
    prt_path = os.path.join(c3_dir, 'PRT.csv')
    org_path = os.path.join(c3_dir, 'ORG.csv')
    ccode_path = os.path.join(c3_dir, 'CCODE.csv')
    pf_path = os.path.join(c3_dir, 'PF.csv')

    required_files = [dd_path, dda_path, ing_path, bna_path, mp_path, prt_path, org_path, ccode_path, pf_path]
    missing = [path for path in required_files if not os.path.exists(path)]
    if missing:
        raise FileNotFoundError(f'缺少 WHODrug 文件: {missing[0]}')

    atc_map = {}
    for row in _read_csv_rows(dda_path):
        if len(row) < 5:
            continue
        key = _build_whodrug_key(row[0], row[1], row[2])
        if key and row[4]:
            atc_map[key] = _clean_text(row[4])

    org_map = {}
    for row in _read_csv_rows(org_path):
        if len(row) >= 2:
            org_map[_clean_text(row[0])] = _clean_text(row[1])

    pf_map = {}
    for row in _read_csv_rows(pf_path):
        if len(row) >= 2:
            pf_map[_clean_text(row[0])] = _clean_text(row[1])

    pt_map = {}
    for row in _read_csv_rows(prt_path):
        if len(row) >= 2:
            pt_map[_clean_text(row[0])] = _clean_text(row[1])

    country_map = {}
    for row in _read_csv_rows(ccode_path):
        if len(row) >= 2:
            country_map[_clean_text(row[0])] = _clean_text(row[1])

    bna_lang = 'ZH' if language == 'cn' else 'EN'
    ingredient_name_map = {}
    for row in _read_csv_rows(bna_path):
        if len(row) < 3:
            continue
        ingredient_code = _clean_text(row[0])
        lang_code = _clean_text(row[1]).upper()
        ingredient_name = _clean_text(row[2])
        if not ingredient_code or not ingredient_name:
            continue
        if lang_code == bna_lang:
            ingredient_name_map[ingredient_code] = ingredient_name
        elif ingredient_code not in ingredient_name_map:
            ingredient_name_map[ingredient_code] = ingredient_name

    ingredient_map = {}
    for row in _read_csv_rows(ing_path):
        if len(row) < 5:
            continue
        key = _build_whodrug_key(row[0], row[1], row[2])
        ingredient_code = _clean_text(row[4])
        ingredient_name = ingredient_name_map.get(ingredient_code, ingredient_code)
        if key and ingredient_name:
            ingredient_map.setdefault(key, [])
            if ingredient_name not in ingredient_map[key]:
                ingredient_map[key].append(ingredient_name)

    mp_map = {}
    for row in _read_csv_rows(mp_path):
        if len(row) < 9:
            continue
        key = _build_whodrug_key(row[2], row[3], row[4])
        if not key:
            continue
        country_code = ''
        for idx in (17, 18, 13):
            if len(row) > idx and _clean_text(row[idx]):
                country_code = _clean_text(row[idx])
                break
        org_code = _clean_text(row[15]) if len(row) > 15 else ''
        mp_map[key] = {
            'mpid': _clean_text(row[5]) if len(row) > 5 else '',
            'drug_name': _clean_text(row[8]) if len(row) > 8 else '',
            'country': country_map.get(country_code, country_code),
            'mah': org_map.get(org_code, org_code),
        }

    records = []
    vector_records = []
    seen = set()
    for row in _read_csv_rows(dd_path):
        if len(row) < 12:
            continue

        key = _build_whodrug_key(row[0], row[1], row[2])
        if not key or key in seen:
            continue
        seen.add(key)

        mp_info = mp_map.get(key, {})
        drug_name = mp_info.get('drug_name') or _clean_text(row[11])
        atc_code = atc_map.get(key, '')
        pt = pt_map.get(_clean_text(row[6]), '')
        substance_name = '; '.join(ingredient_map.get(key, []))
        pharmaceutical_form = pf_map.get(_clean_text(row[6]), '')
        country = mp_info.get('country', '')
        mah = mp_info.get('mah', '')
        mpid = mp_info.get('mpid', '')

        record = WhodrugDrug(
            mpid=mpid,
            drug_code=key,
            drug_name=_limit_text(drug_name or key, 500),
            atc_code=_limit_text(atc_code, 10),
            pt=_limit_text(pt, 100),
            substance_name=_clean_text(substance_name),
            strength='',
            pharmaceutical_form=_limit_text(pharmaceutical_form, 200),
            country=_limit_text(country, 120),
            mah=_limit_text(mah, 500),
            language=language,
            source_file='DD.csv'
        )
        records.append(record)

        vector_text = '\n'.join(filter(None, [
            f'药品名称: {drug_name or key}',
            f'WHODrug编码: {key}',
            f'MPID: {mpid}' if mpid else '',
            f'PT: {pt}' if pt else '',
            f'活性成分: {substance_name}' if substance_name else '',
            f'ATC编码: {atc_code}' if atc_code else '',
            f'剂型: {pharmaceutical_form}' if pharmaceutical_form else '',
            f'国家: {country}' if country else '',
            f'上市许可持有人: {mah}' if mah else '',
            '词典: WHODrug'
        ]))
        vector_records.append({
            'id': f'whodrug-{language}-{key}',
            'text': vector_text,
            'metadata': {
                'drug_code': key,
                'mpid': mpid,
                'drug_name': drug_name or key,
                'pt': pt,
                'substance_name': substance_name,
                'atc_code': atc_code,
                'pharmaceutical_form': pharmaceutical_form,
                'language': language,
                'source_file': 'DD.csv'
            }
        })

    return records, vector_records


def _build_meddra_records(language):
    folder_path = _get_meddra_folder(language)

    soc_to_hlgt = {}
    hlgt_to_soc = {}
    for row in _read_pipe_rows(os.path.join(folder_path, 'soc_hlgt.asc')):
        if len(row) >= 2:
            soc_code = _clean_text(row[0])
            hlgt_code = _clean_text(row[1])
            if soc_code and hlgt_code and hlgt_code not in hlgt_to_soc:
                hlgt_to_soc[hlgt_code] = soc_code
                soc_to_hlgt.setdefault(soc_code, set()).add(hlgt_code)

    hlt_to_hlgt = {}
    for row in _read_pipe_rows(os.path.join(folder_path, 'hlgt_hlt.asc')):
        if len(row) >= 2:
            hlgt_code = _clean_text(row[0])
            hlt_code = _clean_text(row[1])
            if hlgt_code and hlt_code and hlt_code not in hlt_to_hlgt:
                hlt_to_hlgt[hlt_code] = hlgt_code

    pt_to_hlt = {}
    for row in _read_pipe_rows(os.path.join(folder_path, 'hlt_pt.asc')):
        if len(row) >= 2:
            hlt_code = _clean_text(row[0])
            pt_code = _clean_text(row[1])
            if hlt_code and pt_code and pt_code not in pt_to_hlt:
                pt_to_hlt[pt_code] = hlt_code

    pt_to_soc = {}
    for row in _read_pipe_rows(os.path.join(folder_path, 'mdhier.asc')):
        if len(row) >= 4:
            pt_code = _clean_text(row[0])
            hlt_code = _clean_text(row[1])
            hlgt_code = _clean_text(row[2])
            soc_code = _clean_text(row[3])
            if pt_code:
                pt_to_hlt.setdefault(pt_code, hlt_code)
                pt_to_soc.setdefault(pt_code, soc_code)
            if hlt_code:
                hlt_to_hlgt.setdefault(hlt_code, hlgt_code)
            if hlgt_code:
                hlgt_to_soc.setdefault(hlgt_code, soc_code)

    name_maps = _load_meddra_name_maps(folder_path)

    soc_name_map = {code: item['name'] for code, item in name_maps['SOC'].items()}

    records = []
    vector_records = []

    for code, item in name_maps['SOC'].items():
        records.append(MeddraTerm(
            code=code,
            name=item['name'],
            term_level='SOC',
            parent_code='',
            soc_code=code,
            language=language,
            source_file='soc.asc'
        ))

    for code, item in name_maps['HLGT'].items():
        soc_code = hlgt_to_soc.get(code, '')
        records.append(MeddraTerm(
            code=code,
            name=item['name'],
            term_level='HLGT',
            parent_code=soc_code,
            soc_code=soc_code,
            language=language,
            source_file='hlgt.asc'
        ))

    for code, item in name_maps['HLT'].items():
        hlgt_code = hlt_to_hlgt.get(code, '')
        soc_code = hlgt_to_soc.get(hlgt_code, '')
        records.append(MeddraTerm(
            code=code,
            name=item['name'],
            term_level='HLT',
            parent_code=hlgt_code,
            soc_code=soc_code,
            language=language,
            source_file='hlt.asc'
        ))

    for code, item in name_maps['PT'].items():
        hlt_code = pt_to_hlt.get(code, '')
        hlgt_code = hlt_to_hlgt.get(hlt_code, '')
        soc_code = pt_to_soc.get(code) or hlgt_to_soc.get(hlgt_code, '')
        records.append(MeddraTerm(
            code=code,
            name=item['name'],
            term_level='PT',
            parent_code=hlt_code,
            soc_code=soc_code,
            language=language,
            source_file='pt.asc'
        ))

    for code, item in name_maps['LLT'].items():
        row = item['row']
        pt_code = _clean_text(row[2]) if len(row) > 2 else ''
        hlt_code = pt_to_hlt.get(pt_code, '')
        hlgt_code = hlt_to_hlgt.get(hlt_code, '')
        soc_code = pt_to_soc.get(pt_code) or hlgt_to_soc.get(hlgt_code, '')
        records.append(MeddraTerm(
            code=code,
            name=item['name'],
            term_level='LLT',
            parent_code=pt_code,
            soc_code=soc_code,
            language=language,
            source_file='llt.asc'
        ))

    for term in records:
        soc_name = soc_name_map.get(term.soc_code, '')
        vector_text = '\n'.join(filter(None, [
            f'术语名称: {term.name}',
            f'MedDRA编码: {term.code}',
            f'层级: {term.term_level}',
            f'父级编码: {term.parent_code}' if term.parent_code else '',
            f'SOC: {soc_name}' if soc_name else '',
            '词典: MedDRA'
        ]))
        vector_records.append({
            'id': f'meddra-{language}-{term.term_level}-{term.code}',
            'text': vector_text,
            'metadata': {
                'code': term.code,
                'name': term.name,
                'level': term.term_level,
                'parent_code': term.parent_code or '',
                'soc_code': term.soc_code or '',
                'soc_name': soc_name,
                'language': language,
                'source_file': term.source_file or ''
            }
        })

    return records, vector_records


def _build_meddra_smq_records(language):
    folder_path = _get_meddra_folder(language)
    name_maps = _load_meddra_name_maps(folder_path)

    smq_records = []
    smq_term_records = []

    smq_list_path = os.path.join(folder_path, 'smq_list.asc')
    smq_content_path = os.path.join(folder_path, 'smq_content.asc')
    for required_path in (smq_list_path, smq_content_path):
        if not os.path.exists(required_path):
            raise FileNotFoundError(f'缺少 MedDRA SMQ 文件: {required_path}')

    for row in _read_pipe_rows(smq_list_path):
        if len(row) < 2:
            continue
        smq_records.append(MeddraSmq(
            smq_code=_clean_text(row[0]),
            smq_name=_limit_text(row[1], 500),
            smq_level=_limit_text(row[2] if len(row) > 2 else '', 20),
            description=_clean_text(row[3] if len(row) > 3 else ''),
            source_text=_clean_text(row[4] if len(row) > 4 else ''),
            note_text=_clean_text(row[5] if len(row) > 5 else ''),
            meddra_version=_limit_text(row[6] if len(row) > 6 else '', 20),
            status=_limit_text(row[7] if len(row) > 7 else '', 10),
            algorithmic_flag=_limit_text(row[8] if len(row) > 8 else '', 10),
            language=language,
            source_file='smq_list.asc'
        ))

    for row in _read_pipe_rows(smq_content_path):
        if len(row) < 2:
            continue
        term_level_num = _clean_text(row[2] if len(row) > 2 else '')
        term_level = MEDDRA_LEVEL_NUM_MAP.get(term_level_num, term_level_num)
        term_code = _clean_text(row[1])
        term_name, resolved_level = _lookup_meddra_term(name_maps, term_code, term_level)
        smq_term_records.append(MeddraSmqTerm(
            smq_code=_clean_text(row[0]),
            term_code=term_code,
            term_name=_limit_text(term_name, 500),
            term_level=_limit_text(resolved_level or term_level, 10),
            scope=_limit_text(row[3] if len(row) > 3 else '', 10),
            category=_limit_text(row[4] if len(row) > 4 else '', 10),
            weight=_limit_text(row[5] if len(row) > 5 else '', 20),
            term_status=_limit_text(row[6] if len(row) > 6 else '', 10),
            term_add_version=_limit_text(row[7] if len(row) > 7 else '', 20),
            smq_add_version=_limit_text(row[8] if len(row) > 8 else '', 20),
            language=language,
            source_file='smq_content.asc'
        ))

    return smq_records, smq_term_records


def _get_meddra_doc_specs(language, include_reference=False):
    release_dir = _get_meddra_release_folder(language)
    specs = [
        ('intguide', 'MedDRA入门指南' if language == 'cn' else 'MedDRA Intro Guide'),
        ('SMQ_intguide', 'MedDRA SMQ指南' if language == 'cn' else 'MedDRA SMQ Guide'),
        ('dist_file_format', 'MedDRA文件格式说明' if language == 'cn' else 'MedDRA File Format Guide'),
    ]
    if include_reference:
        specs.extend([
            ('whatsnew', 'MedDRA版本更新说明' if language == 'cn' else 'MedDRA What\'s New'),
            ('detail_report', 'MedDRA详细版本报告' if language == 'cn' else 'MedDRA Detail Report'),
        ])

    results = []
    for prefix, label in specs:
        matches = sorted(
            filename for filename in os.listdir(release_dir)
            if filename.lower().startswith(prefix.lower()) and filename.lower().endswith('.pdf')
        )
        if matches:
            results.append({
                'label': label,
                'source_path': os.path.join(release_dir, matches[0]),
                'file_name': matches[0],
            })
    if not results:
        raise FileNotFoundError(f'未在 {release_dir} 下找到 MedDRA PDF 指南文件')
    return results


def _build_meddra_guidance_records(language, include_reference=False):
    vector_service = VectorService()
    records = []
    imported = []

    for spec in _get_meddra_doc_specs(language, include_reference=include_reference):
        file_ext = spec['file_name'].rsplit('.', 1)[1].lower()
        text = vector_service._load_file(spec['source_path'], file_ext)
        if not text.strip():
            continue

        chunks = vector_service.text_splitter.split_text(text)
        for index, chunk in enumerate(chunks):
            records.append({
                'id': f"meddra-guidance-{language}-{spec['file_name']}-{index}",
                'text': chunk,
                'metadata': {
                    'source': spec['file_name'],
                    'title': spec['label'],
                    'language': language,
                    'doc_type': 'meddra_guidance',
                    'chunk_index': index,
                }
            })

        imported.append({
            'file_name': spec['file_name'],
            'chunk_count': len(chunks),
        })

    return records, imported


def _import_meddra_docs(language, include_reference=False):
    records, imported = _build_meddra_guidance_records(language, include_reference=include_reference)
    collection_name = f'meddra_guidance_{language}'
    VectorService().rebuild_collection(collection_name, records)
    return collection_name, imported


def _save_in_batches(records, batch_size=1000):
    count = 0
    batch = []
    for record in records:
        batch.append(record)
        count += 1
        if len(batch) >= batch_size:
            db.session.bulk_save_objects(batch)
            db.session.commit()
            batch = []

    if batch:
        db.session.bulk_save_objects(batch)
        db.session.commit()
    return count


@medical_import_bp.route('/whodrug', methods=['POST'])
@admin_required
def import_whodrug():
    """导入 WHODrug 数据"""
    data = request.get_json() or {}
    language = data.get('language', 'cn')
    lock_key = f'whodrug_{language}'

    if not _acquire_import_lock(lock_key):
        return error(f'WHODrug {language} 正在导入中，请勿重复操作')

    import_log = ImportLog(
        user_id=g.user_id,
        dict_type=lock_key,
        file_name=f'WHODrug {language}',
        status='running'
    )
    db.session.add(import_log)
    db.session.commit()

    try:
        records, _ = _build_whodrug_records(language)
        db.session.query(WhodrugDrug).filter_by(language=language).delete(synchronize_session=False)
        db.session.commit()

        count = _save_in_batches(records)

        import_log.record_count = count
        import_log.status = 'success'
        import_log.complete_time = datetime.now()
        db.session.commit()
        return success({'count': count}, f'成功导入 {count} 条 WHODrug {language} 数据')
    except Exception as e:
        db.session.rollback()
        import_log.status = 'failed'
        import_log.error_message = str(e)
        import_log.complete_time = datetime.now()
        db.session.commit()
        return error(f'导入失败: {str(e)}')
    finally:
        _release_import_lock(lock_key)


@medical_import_bp.route('/meddra', methods=['POST'])
@admin_required
def import_meddra():
    """导入 MedDRA 数据"""
    data = request.get_json() or {}
    language = data.get('language', 'cn')
    lock_key = f'meddra_{language}'

    if not _acquire_import_lock(lock_key):
        return error(f'MedDRA {language} 正在导入中，请勿重复操作')

    import_log = ImportLog(
        user_id=g.user_id,
        dict_type=lock_key,
        file_name=f'MedDRA {language}',
        status='running'
    )
    db.session.add(import_log)
    db.session.commit()

    try:
        records, vector_records = _build_meddra_records(language)
        db.session.query(MeddraTerm).filter_by(language=language).delete(synchronize_session=False)
        db.session.commit()

        count = _save_in_batches(records)

        try:
            VectorService().rebuild_collection(f'meddra_{language}', vector_records)
        except OllamaServiceError:
            pass

        import_log.record_count = count
        import_log.status = 'success'
        import_log.complete_time = datetime.now()
        db.session.commit()
        return success({'count': count}, f'成功导入 {count} 条 MedDRA {language} 数据')
    except Exception as e:
        db.session.rollback()
        import_log.status = 'failed'
        import_log.error_message = str(e)
        import_log.complete_time = datetime.now()
        db.session.commit()
        return error(f'导入失败: {str(e)}')
    finally:
        _release_import_lock(lock_key)


@medical_import_bp.route('/meddra_smq', methods=['POST'])
@admin_required
def import_meddra_smq():
    """导入 MedDRA SMQ 数据"""
    data = request.get_json() or {}
    language = data.get('language', 'cn')
    lock_key = f'smq_{language}'

    if not _acquire_import_lock(lock_key):
        return error(f'MedDRA SMQ {language} 正在导入中，请勿重复操作')

    import_log = ImportLog(
        user_id=g.user_id,
        dict_type=lock_key,
        file_name=f'MedDRA SMQ {language}',
        status='running'
    )
    db.session.add(import_log)
    db.session.commit()

    try:
        smq_records, smq_term_records = _build_meddra_smq_records(language)
        db.session.query(MeddraSmqTerm).filter_by(language=language).delete(synchronize_session=False)
        db.session.query(MeddraSmq).filter_by(language=language).delete(synchronize_session=False)
        db.session.commit()

        count = _save_in_batches(smq_records)
        count += _save_in_batches(smq_term_records)

        import_log.record_count = count
        import_log.status = 'success'
        import_log.complete_time = datetime.now()
        db.session.commit()
        return success({'count': count}, f'成功导入 {count} 条 MedDRA SMQ {language} 数据')
    except Exception as e:
        db.session.rollback()
        import_log.status = 'failed'
        import_log.error_message = str(e)
        import_log.complete_time = datetime.now()
        db.session.commit()
        return error(f'导入失败: {str(e)}')
    finally:
        _release_import_lock(lock_key)


@medical_import_bp.route('/meddra_docs', methods=['POST'])
@admin_required
def import_meddra_docs():
    """批量导入 MedDRA 指南文档并向量化"""
    data = request.get_json() or {}
    language = data.get('language', 'cn')
    include_reference = bool(data.get('include_reference', False))
    lock_key = f'md_docs_{language}'

    if not _acquire_import_lock(lock_key):
        return error(f'MedDRA 文档 {language} 正在导入中，请勿重复操作')

    import_log = ImportLog(
        user_id=g.user_id,
        dict_type=lock_key,
        file_name=f'MedDRA Docs {language}',
        status='running'
    )
    db.session.add(import_log)
    db.session.commit()

    try:
        collection_name, imported_docs = _import_meddra_docs(language, include_reference=include_reference)
        import_log.record_count = len(imported_docs)
        import_log.status = 'success'
        import_log.complete_time = datetime.now()
        db.session.commit()
        return success({
            'collection_name': collection_name,
            'count': len(imported_docs),
            'documents': imported_docs
        }, f'成功导入 {len(imported_docs)} 个 MedDRA 文档')
    except Exception as e:
        db.session.rollback()
        import_log.status = 'failed'
        import_log.error_message = str(e)
        import_log.complete_time = datetime.now()
        db.session.commit()
        return error(f'导入失败: {str(e)}')
    finally:
        _release_import_lock(lock_key)


@medical_import_bp.route('/logs', methods=['GET'])
@admin_required
def get_logs():
    """获取导入日志列表"""
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', type=int)
    if page_size is None:
        page_size = request.args.get('pageSize', 20, type=int)

    query = ImportLog.query.order_by(ImportLog.create_time.desc())
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)

    items = [item.to_dict() for item in pagination.items]
    return page_response(items, pagination.total, page, page_size)


@medical_import_bp.route('/status', methods=['GET'])
@admin_required
def get_status():
    """获取数据导入状态"""
    whodrug_en = db.session.query(func.count(WhodrugDrug.id)).filter_by(language='en').scalar()
    whodrug_cn = db.session.query(func.count(WhodrugDrug.id)).filter_by(language='cn').scalar()
    meddra_en = db.session.query(func.count(MeddraTerm.id)).filter_by(language='en').scalar()
    meddra_cn = db.session.query(func.count(MeddraTerm.id)).filter_by(language='cn').scalar()
    smq_en = db.session.query(func.count(MeddraSmq.id)).filter_by(language='en').scalar()
    smq_cn = db.session.query(func.count(MeddraSmq.id)).filter_by(language='cn').scalar()
    smq_term_en = db.session.query(func.count(MeddraSmqTerm.id)).filter_by(language='en').scalar()
    smq_term_cn = db.session.query(func.count(MeddraSmqTerm.id)).filter_by(language='cn').scalar()

    last_log = ImportLog.query.order_by(ImportLog.create_time.desc()).first()
    return success({
        'dict_path': DICT_PATH,
        'whodrug': {'en': whodrug_en, 'cn': whodrug_cn},
        'meddra': {'en': meddra_en, 'cn': meddra_cn},
        'smq': {'en': smq_en, 'cn': smq_cn},
        'smq_terms': {'en': smq_term_en, 'cn': smq_term_cn},
        'last_import': last_log.to_dict() if last_log else None
    })
