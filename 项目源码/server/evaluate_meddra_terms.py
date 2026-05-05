"""
离线小批量评测 MedDRA 术语解释质量

示例:
  python evaluate_meddra_terms.py --language cn --terms "肺局部纤维条索影" "胸闷气短"
  python evaluate_meddra_terms.py --language cn --terms-file ./terms.txt --output ./reports/meddra_eval.json
"""
import argparse
import json
import os
from datetime import datetime

from app import create_app
from services.meddra_explain_service import MeddraExplainService


def _load_terms(args):
    terms = []

    for term in args.terms or []:
        cleaned = str(term or '').strip()
        if cleaned and cleaned not in terms:
            terms.append(cleaned)

    if args.terms_file:
        with open(args.terms_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                cleaned = line.strip()
                if cleaned and cleaned not in terms:
                    terms.append(cleaned)

    return terms


def _default_output_path():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')
    os.makedirs(report_dir, exist_ok=True)
    return os.path.join(report_dir, f'meddra_eval_{timestamp}.json')


def _build_summary(result):
    items = result.get('items') or []
    passed = [item for item in items if item.get('passed')]
    failed = [item for item in items if not item.get('passed')]
    return {
        'total': len(items),
        'passed': len(passed),
        'failed': len(failed),
        'pass_rate': round((len(passed) / len(items)) * 100, 2) if items else 0,
        'failed_terms': [
            {
                'term': item.get('term'),
                'status': item.get('status'),
                'final_score': item.get('final_score', 0)
            }
            for item in failed
        ]
    }


def main():
    parser = argparse.ArgumentParser(description='离线评测 MedDRA 术语解释质量')
    parser.add_argument('--language', default='cn', help='语言: cn/en')
    parser.add_argument('--terms', nargs='*', default=[], help='直接传入术语列表')
    parser.add_argument('--terms-file', help='从文本文件按行读取术语')
    parser.add_argument('--threshold', type=int, default=80, help='通过阈值，默认80')
    parser.add_argument('--max-iterations', type=int, default=1, help='最大迭代轮数，默认1')
    parser.add_argument('--output', help='输出 JSON 文件路径')
    parser.add_argument('--use-llm-judge', action='store_true', help='启用 LLM Judge')
    parser.add_argument('--generator-mode', default='hybrid', choices=['hybrid', 'full'], help='Generator 模式')
    args = parser.parse_args()

    terms = _load_terms(args)
    if not terms:
        raise SystemExit('请通过 --terms 或 --terms-file 提供至少一个术语')

    os.environ['EXPLAIN_USE_LLM_JUDGE'] = '1' if args.use_llm_judge else '0'
    os.environ['EXPLAIN_GENERATOR_MODE'] = args.generator_mode

    app = create_app()
    with app.app_context():
        service = MeddraExplainService()
        result = service.explain_batch(
            terms,
            language=args.language,
            threshold=args.threshold,
            max_iterations=args.max_iterations
        )

    report = {
        'meta': {
            'language': args.language,
            'threshold': args.threshold,
            'max_iterations': args.max_iterations,
            'use_llm_judge': args.use_llm_judge,
            'generator_mode': args.generator_mode,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        },
        'summary': _build_summary(result),
        'result': result
    }

    output_path = args.output or _default_output_path()
    output_dir = os.path.dirname(os.path.abspath(output_path))
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(json.dumps({
        'summary': report['summary'],
        'output': output_path
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
