"""
命令行导入医学词典，绕过前端超时

用法:
  python import_dicts.py whodrug cn
  python import_dicts.py whodrug en
  python import_dicts.py meddra cn
  python import_dicts.py meddra en
  python import_dicts.py smq cn
  python import_dicts.py smq en
  python import_dicts.py meddra_docs cn
  python import_dicts.py meddra_docs en
"""
import sys
from datetime import datetime

from app import create_app
from models import db
from models.import_log import ImportLog
from models.meddra import MeddraTerm
from models.meddra_smq import MeddraSmq, MeddraSmqTerm
from models.whodrug import WhodrugDrug
from routes.medical_import import (
    _build_meddra_smq_records,
    _build_meddra_records,
    _build_whodrug_records,
    _import_meddra_docs,
    _save_in_batches,
)
from services.vector_service import OllamaServiceError, VectorService


def run_import(dict_type, language):
    app = create_app()
    with app.app_context():
        import_log = ImportLog(
            user_id=1,
            dict_type=f'{dict_type}_{language}',
            file_name=f'{dict_type}_{language}',
            status='running'
        )
        db.session.add(import_log)
        db.session.commit()

        try:
            if dict_type == 'whodrug':
                print(f'开始构建 WHODrug {language} 记录...')
                records, _ = _build_whodrug_records(language)
                db.session.query(WhodrugDrug).filter_by(language=language).delete(synchronize_session=False)
            elif dict_type == 'meddra':
                print(f'开始构建 MedDRA {language} 记录...')
                records, vector_records = _build_meddra_records(language)
                db.session.query(MeddraTerm).filter_by(language=language).delete(synchronize_session=False)
                collection_name = f'meddra_{language}'
            elif dict_type == 'smq':
                print(f'开始构建 MedDRA SMQ {language} 记录...')
                smq_records, smq_term_records = _build_meddra_smq_records(language)
                db.session.query(MeddraSmqTerm).filter_by(language=language).delete(synchronize_session=False)
                db.session.query(MeddraSmq).filter_by(language=language).delete(synchronize_session=False)
                db.session.commit()
                print(f'开始写入 SMQ 主表，共 {len(smq_records)} 条...')
                count = _save_in_batches(smq_records)
                print(f'开始写入 SMQ 术语映射表，共 {len(smq_term_records)} 条...')
                count += _save_in_batches(smq_term_records)
                print(f'SMQ 数据库写入完成: {count} 条')
                import_log.record_count = count
                import_log.status = 'success'
                import_log.complete_time = datetime.now()
                db.session.commit()
                print('导入成功')
                return
            elif dict_type == 'meddra_docs':
                print(f'开始导入 MedDRA 说明文档 {language}...')
                collection_name, imported_docs = _import_meddra_docs(language)
                count = len(imported_docs)
                print(f'已导入到内部向量集合: {collection_name}')
                for item in imported_docs:
                    print(f"- {item['file_name']}: {item['chunk_count']} chunks")
                import_log.record_count = count
                import_log.status = 'success'
                import_log.complete_time = datetime.now()
                db.session.commit()
                print('导入成功')
                return
            else:
                raise ValueError('dict_type 仅支持 whodrug、meddra、smq 或 meddra_docs')

            db.session.commit()
            print(f'开始写入数据库，共 {len(records)} 条...')
            count = _save_in_batches(records)
            print(f'数据库写入完成: {count} 条')

            if dict_type == 'meddra':
                try:
                    print(f'开始重建向量集合: {collection_name}')
                    VectorService().rebuild_collection(collection_name, vector_records)
                    print('向量集合重建完成')
                except OllamaServiceError as exc:
                    print(f'向量集合未重建: {exc}')
            else:
                print('WHODrug 默认跳过向量集合构建')

            import_log.record_count = count
            import_log.status = 'success'
            import_log.complete_time = datetime.now()
            db.session.commit()
            print('导入成功')
        except Exception as exc:
            db.session.rollback()
            import_log.status = 'failed'
            import_log.error_message = str(exc)
            import_log.complete_time = datetime.now()
            db.session.commit()
            print(f'导入失败: {exc}')
            raise


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    dict_type = sys.argv[1].strip().lower()
    language = sys.argv[2].strip().lower()
    run_import(dict_type, language)


if __name__ == '__main__':
    main()
