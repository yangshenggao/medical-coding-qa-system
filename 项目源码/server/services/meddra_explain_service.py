"""
MedDRA 小批量解释验证服务
实现 Retriever / Generator / Judge / Verifier 协同与反馈迭代
"""
import json
import re

from flask import current_app
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from models.meddra_smq import MeddraSmq, MeddraSmqTerm
from services.rag_service import RAGService

GENERATOR_SYSTEM_PROMPT = """你是 MedDRA 编码解释生成代理（Generator）。

你会拿到：
1. 用户输入术语
2. MedDRA 候选术语证据
3. MedDRA 规则说明文档证据
4. SMQ 相关证据
5. 来自 Judge / Verifier 的修正反馈（可能为空）

请从不同医学维度给出解释说明，并只输出 JSON，不要输出额外文字。

JSON 要求：
{{
  "term": "用户原语",
  "selected_term": {{
    "code": "候选代码",
    "name": "候选术语名称",
    "level": "LLT/PT/HLT/HLGT/SOC"
  }},
  "candidate_terms": [
    {{
      "code": "候选代码",
      "name": "候选名称",
      "level": "层级",
      "reason": "简要理由"
    }}
  ],
  "medical_dimensions": {{
    "clinical_semantics": "从临床语义解释原语含义",
    "coding_rationale": "为什么推荐这个术语/编码",
    "hierarchy_interpretation": "层级关系如何理解",
    "smq_relevance": "与 SMQ 的关系，没有则说明未命中",
    "ambiguity_and_risk": "歧义、风险与人工复核点"
  }},
  "summary": "面向编码员的简短总结",
  "confidence": 0,
  "needs_manual_review": true,
  "evidence_refs": ["来源1", "来源2"],
  "feedback_applied": ["你根据反馈修了什么"]
}}

硬性要求：
1. 只能从候选证据里选择 selected_term.code
2. confidence 取 0-100 的整数
3. needs_manual_review 必须是布尔值
4. medical_dimensions 里的 5 个字段都必须有内容
5. 如果证据不足，要明确写出人工复核风险
"""

HYBRID_GENERATOR_SYSTEM_PROMPT = """你是 MedDRA 编码解释补全代理（Generator）。

你会收到一个已经由程序生成的结构化解释骨架，请只补全两个字段：
1. coding_rationale
2. ambiguity_and_risk

要求：
1. 只能基于给定骨架和证据补全
2. 输出必须是 JSON
3. 不要修改其它字段
4. 文字要简洁，适合本地小模型快速返回
"""

JUDGE_SYSTEM_PROMPT = """你是 MedDRA 解释质量评审代理（Judge）。

你会拿到用户术语、证据上下文和 Generator 的 JSON 输出。请从以下维度评分：
1. 事实一致性：是否严格受限于候选术语和规则证据
2. 编码合理性：推荐术语是否站得住脚
3. 医学解释完整性：是否覆盖临床语义、编码理由、层级、SMQ、风险
4. 可审计性：是否说明证据来源与人工复核点
5. 结构质量：JSON 是否清晰且字段完整

只输出 JSON：
{{
  "score": 0,
  "pass": false,
  "strengths": ["..."],
  "issues": ["..."],
  "must_fix": ["..."],
  "feedback_for_generator": ["..."]
}}

要求：
1. score 为 0-100 整数
2. pass 的阈值由用户传入，不要自行更改
3. 如果 selected_term 不在候选证据里，必须判定不通过
4. 如果缺少人工复核提示，必须扣分
"""


class MeddraExplainService:
    """MedDRA 小批量解释服务"""

    def __init__(self):
        self.rag_service = RAGService()
        self.generator_llm = ChatOllama(
            model=current_app.config['OLLAMA_LLM_MODEL'],
            base_url=current_app.config['OLLAMA_BASE_URL'],
            temperature=0.2,
            timeout=current_app.config['EXPLAIN_LLM_TIMEOUT'],
            format='json',
            num_predict=current_app.config['EXPLAIN_JSON_MAX_TOKENS']
        )
        self.judge_llm = ChatOllama(
            model=current_app.config['OLLAMA_JUDGE_MODEL'],
            base_url=current_app.config['OLLAMA_BASE_URL'],
            temperature=0,
            timeout=current_app.config['JUDGE_LLM_TIMEOUT'],
            format='json',
            num_predict=current_app.config['JUDGE_JSON_MAX_TOKENS']
        )
        self.max_terms = current_app.config['EXPLAIN_BATCH_MAX_TERMS']
        self.max_iterations = current_app.config['EXPLAIN_MAX_ITERATIONS']
        self.pass_score = current_app.config['EXPLAIN_PASS_SCORE']
        self.term_top_k = current_app.config['EXPLAIN_RETRIEVE_TOP_K']
        self.guidance_top_k = current_app.config['EXPLAIN_GUIDANCE_TOP_K']
        self.use_llm_judge = current_app.config['EXPLAIN_USE_LLM_JUDGE']
        self.generator_mode = current_app.config['EXPLAIN_GENERATOR_MODE']

    def _build_chain(self, llm, system_prompt):
        prompt = ChatPromptTemplate.from_messages([
            ('system', system_prompt),
            ('human', '{payload}')
        ])
        return prompt | llm | StrOutputParser()

    def _safe_json_loads(self, text):
        if isinstance(text, dict):
            return text

        candidate = (text or '').strip()
        if not candidate:
            return None

        try:
            return json.loads(candidate)
        except Exception:
            pass

        fenced = re.search(r'```json\s*(\{.*?\})\s*```', candidate, flags=re.S)
        if fenced:
            try:
                return json.loads(fenced.group(1))
            except Exception:
                pass

        first = candidate.find('{')
        last = candidate.rfind('}')
        if first != -1 and last != -1 and last > first:
            try:
                return json.loads(candidate[first:last + 1])
            except Exception:
                return None
        return None

    def _extract_candidate_codes(self, docs):
        candidates = []
        for doc in docs:
            source = doc.get('source', '')
            match = re.match(r'MedDRA/([^/]+)/(.+)', source)
            if not match:
                continue
            candidates.append({
                'level': match.group(1),
                'code': match.group(2),
                'source': source,
                'content': doc.get('content', '')
            })
        return candidates

    def _search_smq_docs(self, candidate_docs, language, limit=5):
        candidate_codes = [item['code'] for item in self._extract_candidate_codes(candidate_docs)]
        if not candidate_codes:
            return []

        try:
            rows = MeddraSmqTerm.query.filter(
                MeddraSmqTerm.language == language,
                MeddraSmqTerm.term_code.in_(candidate_codes)
            ).limit(limit).all()
        except Exception as exc:
            current_app.logger.warning(f'SMQ 查询已降级跳过: {exc}')
            return []

        if not rows:
            return []

        smq_codes = [row.smq_code for row in rows]
        try:
            smq_map = {
                row.smq_code: row for row in MeddraSmq.query.filter(
                    MeddraSmq.language == language,
                    MeddraSmq.smq_code.in_(smq_codes)
                ).all()
            }
        except Exception as exc:
            current_app.logger.warning(f'SMQ 主表查询已降级跳过: {exc}')
            smq_map = {}

        docs = []
        for row in rows:
            smq = smq_map.get(row.smq_code)
            docs.append({
                'source': f'SMQ/{row.smq_code}',
                'content': '\n'.join(filter(None, [
                    f'SMQ名称: {smq.smq_name}' if smq else '',
                    f'SMQ代码: {row.smq_code}',
                    f'命中术语: {row.term_name or row.term_code}',
                    f'术语层级: {row.term_level}' if row.term_level else '',
                    f'检索范围: {row.scope}' if row.scope else '',
                    f'类别: {row.category}' if row.category else '',
                    f'说明: {smq.note_text[:200]}' if smq and smq.note_text else ''
                ]))
            })
        return docs

    def _compact_docs(self, docs, limit=8, max_chars=500):
        compacted = []
        for doc in docs[:limit]:
            compacted.append({
                'source': doc.get('source', ''),
                'content': str(doc.get('content', ''))[:max_chars]
            })
        return compacted

    def _build_context(self, term, language):
        term_docs = self.rag_service._search_meddra_docs(term, limit=self.term_top_k)
        guidance_docs = self.rag_service._search_meddra_guidance_docs(term, language, limit=self.guidance_top_k)
        smq_docs = self._search_smq_docs(term_docs, language)
        context_docs = self._compact_docs(term_docs, limit=5, max_chars=400)
        context_docs.extend(self._compact_docs(guidance_docs, limit=3, max_chars=350))
        context_docs.extend(self._compact_docs(smq_docs, limit=3, max_chars=300))
        return {
            'term_docs': term_docs,
            'guidance_docs': guidance_docs,
            'smq_docs': smq_docs,
            'all_docs': context_docs,
            'candidate_codes': [item['code'] for item in self._extract_candidate_codes(term_docs)]
        }

    def _extract_candidate_terms(self, term_docs, limit=3):
        candidates = []
        for doc in term_docs[:limit]:
            source = doc.get('source', '')
            match = re.match(r'MedDRA/([^/]+)/(.+)', source)
            if not match:
                continue
            level = match.group(1)
            code = match.group(2)
            name_match = re.search(r'术语名称:\s*(.+)', doc.get('content', ''))
            name = name_match.group(1).strip() if name_match else ''
            candidates.append({
                'code': code,
                'name': name,
                'level': level,
                'reason': '来自检索候选，需结合规则与人工复核判断'
            })
        return candidates

    def _extract_guidance_summary(self, guidance_docs):
        if not guidance_docs:
            return '未命中额外规则文档，主要依据术语候选进行解释。'
        first = guidance_docs[0]
        content = str(first.get('content', ''))
        content = re.sub(r'\s+', ' ', content).strip()
        return content[:160] if content else '已命中 MedDRA 规则文档。'

    def _extract_smq_summary(self, smq_docs):
        if not smq_docs:
            return '当前候选术语未命中可用 SMQ 证据，或 SMQ 数据未导入。'
        first = smq_docs[0]
        content = re.sub(r'\s+', ' ', str(first.get('content', ''))).strip()
        return content[:160]

    def _build_hybrid_skeleton(self, term, context):
        candidates = self._extract_candidate_terms(context['term_docs'])
        selected = candidates[0] if candidates else {'code': '', 'name': '', 'level': ''}
        return {
            'term': term,
            'selected_term': {
                'code': selected.get('code', ''),
                'name': selected.get('name', ''),
                'level': selected.get('level', '')
            },
            'candidate_terms': candidates,
            'medical_dimensions': {
                'clinical_semantics': f'原语“{term}”需要在 MedDRA 中映射到更标准的医学术语表达，当前解释基于候选术语与规则证据。',
                'coding_rationale': '待模型补全',
                'hierarchy_interpretation': f"当前优先候选层级为 {selected.get('level', '') or '未知'}，编码时需确认是否应落在更细的 LLT 或更标准的 PT。",
                'smq_relevance': self._extract_smq_summary(context['smq_docs']),
                'ambiguity_and_risk': '待模型补全'
            },
            'summary': f"当前首选候选为 {selected.get('name', '') or '未确定'}（{selected.get('code', '') or '无代码'}），建议结合影像学上下文和人工复核进一步确认。",
            'confidence': 65,
            'needs_manual_review': True,
            'evidence_refs': [doc.get('source', '') for doc in context['all_docs'][:5]],
            'feedback_applied': [],
            'guidance_summary': self._extract_guidance_summary(context['guidance_docs'])
        }

    def _run_generator(self, term, context_docs, feedback, iteration):
        payload = json.dumps({
            'term': term,
            'iteration': iteration,
            'feedback': feedback or [],
            'context': context_docs
        }, ensure_ascii=False)
        chain = self._build_chain(self.generator_llm, GENERATOR_SYSTEM_PROMPT)
        raw = chain.invoke({'payload': payload})
        parsed = self._safe_json_loads(raw)
        return raw, parsed

    def _run_hybrid_generator(self, term, context, feedback, iteration):
        skeleton = self._build_hybrid_skeleton(term, context)
        payload = json.dumps({
            'term': term,
            'iteration': iteration,
            'feedback': feedback or [],
            'skeleton': skeleton,
            'evidence': context['all_docs']
        }, ensure_ascii=False)
        chain = self._build_chain(self.generator_llm, HYBRID_GENERATOR_SYSTEM_PROMPT)
        raw = chain.invoke({'payload': payload})
        parsed = self._safe_json_loads(raw)

        if isinstance(parsed, dict):
            medical_dimensions = parsed.get('medical_dimensions') or {}
            coding_rationale = str(medical_dimensions.get('coding_rationale', '') or parsed.get('coding_rationale', '')).strip()
            ambiguity_and_risk = str(medical_dimensions.get('ambiguity_and_risk', '') or parsed.get('ambiguity_and_risk', '')).strip()
            if coding_rationale:
                skeleton['medical_dimensions']['coding_rationale'] = coding_rationale
            if ambiguity_and_risk:
                skeleton['medical_dimensions']['ambiguity_and_risk'] = ambiguity_and_risk
            feedback_applied = parsed.get('feedback_applied')
            if isinstance(feedback_applied, list):
                skeleton['feedback_applied'] = feedback_applied
            confidence = parsed.get('confidence')
            if isinstance(confidence, int):
                skeleton['confidence'] = confidence

        if skeleton['medical_dimensions']['coding_rationale'] == '待模型补全':
            skeleton['medical_dimensions']['coding_rationale'] = '当前依据检索到的 MedDRA 候选术语及规则文档进行匹配，建议优先核对首选候选与原始描述的一致性。'
        if skeleton['medical_dimensions']['ambiguity_and_risk'] == '待模型补全':
            skeleton['medical_dimensions']['ambiguity_and_risk'] = '该描述仍存在术语歧义，需结合完整影像学语境、诊断背景和编码规范进行人工复核。'

        return raw, skeleton

    def _run_judge(self, term, context_docs, generation, threshold):
        payload = json.dumps({
            'term': term,
            'threshold': threshold,
            'context': context_docs,
            'generation': generation
        }, ensure_ascii=False)
        chain = self._build_chain(self.judge_llm, JUDGE_SYSTEM_PROMPT)
        raw = chain.invoke({'payload': payload})
        parsed = self._safe_json_loads(raw)
        return raw, parsed

    def _run_rule_judge(self, parsed_generation, verifier_result, threshold):
        strengths = []
        issues = list(verifier_result.get('issues') or [])
        must_fix = list(verifier_result.get('issues') or [])
        feedback = []

        if parsed_generation:
            selected = parsed_generation.get('selected_term') or {}
            if selected.get('code'):
                strengths.append('已在候选范围内给出选定术语')

            candidate_terms = parsed_generation.get('candidate_terms') or []
            if isinstance(candidate_terms, list) and candidate_terms:
                strengths.append('提供了候选术语列表')
            else:
                issues.append('未提供 candidate_terms 候选列表')
                must_fix.append('补充 candidate_terms')

            summary = str(parsed_generation.get('summary', '')).strip()
            if len(summary) >= 20:
                strengths.append('提供了编码摘要')
            else:
                issues.append('summary 过短')
                must_fix.append('补充更完整的 summary')

            confidence = parsed_generation.get('confidence')
            if isinstance(confidence, int):
                strengths.append('提供了结构化置信分')
            else:
                issues.append('confidence 非整数')
                must_fix.append('confidence 使用 0-100 整数')

            if parsed_generation.get('needs_manual_review') is True:
                strengths.append('明确提示了人工复核')
            else:
                issues.append('缺少明确人工复核提示')
                must_fix.append('needs_manual_review 需明确为 true/false')
        else:
            issues.append('生成结果为空')
            must_fix.append('输出合法 JSON')

        base_score = 90 if verifier_result.get('ok') else int(verifier_result.get('score_cap', 65))
        deductions = min(len(issues) * 6, 40)
        score = max(0, base_score - deductions)
        passed = verifier_result.get('ok', False) and score >= threshold

        if issues:
            feedback.append('根据规则检查补全缺失字段，并确保 selected_term 取自候选集合')
        if '缺少明确人工复核提示' in issues:
            feedback.append('补充人工复核风险说明')
        if '未提供 candidate_terms 候选列表' in issues:
            feedback.append('至少返回 1-3 个候选术语及理由')

        return {
            'score': score,
            'pass': passed,
            'strengths': strengths,
            'issues': issues,
            'must_fix': must_fix,
            'feedback_for_generator': feedback
        }

    def _run_verifier(self, parsed_generation, candidate_codes):
        issues = []
        if not parsed_generation:
            issues.append('Generator 未返回可解析 JSON')
            return {'ok': False, 'issues': issues, 'score_cap': 40}

        selected = parsed_generation.get('selected_term') or {}
        selected_code = str(selected.get('code', '')).strip()
        if not selected_code:
            issues.append('缺少 selected_term.code')
        elif candidate_codes and selected_code not in candidate_codes:
            issues.append('selected_term.code 不在检索候选集中')

        medical_dimensions = parsed_generation.get('medical_dimensions') or {}
        required_fields = [
            'clinical_semantics',
            'coding_rationale',
            'hierarchy_interpretation',
            'smq_relevance',
            'ambiguity_and_risk'
        ]
        for field in required_fields:
            if not str(medical_dimensions.get(field, '')).strip():
                issues.append(f'缺少 medical_dimensions.{field}')

        confidence = parsed_generation.get('confidence')
        if not isinstance(confidence, int):
            issues.append('confidence 不是整数')

        if not isinstance(parsed_generation.get('needs_manual_review'), bool):
            issues.append('needs_manual_review 不是布尔值')

        evidence_refs = parsed_generation.get('evidence_refs')
        if not isinstance(evidence_refs, list) or not evidence_refs:
            issues.append('evidence_refs 为空或格式不合法')

        summary = str(parsed_generation.get('summary', '')).strip()
        if len(summary) < 20:
            issues.append('summary 过短，缺少足够解释')

        return {
            'ok': not issues,
            'issues': issues,
            'score_cap': 100 if not issues else 65
        }

    def _fallback_result(self, term, context, error_message):
        candidate_preview = []
        for item in self._extract_candidate_codes(context['term_docs'])[:3]:
            candidate_preview.append({
                'code': item['code'],
                'level': item['level'],
                'reason': '回退结果：仅保留检索候选，未完成生成评审闭环'
            })
        return {
            'term': term,
            'status': 'fallback',
            'iterations_used': 0,
            'passed': False,
            'final_score': 0,
            'result': {
                'term': term,
                'selected_term': {},
                'candidate_terms': candidate_preview,
                'medical_dimensions': {},
                'summary': '当前仅返回检索候选，建议人工复核后再编码。',
                'confidence': 0,
                'needs_manual_review': True,
                'evidence_refs': [doc.get('source', '') for doc in context['all_docs'][:5]],
                'feedback_applied': []
            },
            'judge': {
                'score': 0,
                'pass': False,
                'issues': [error_message],
                'must_fix': [error_message],
                'feedback_for_generator': []
            },
            'verifier': {
                'ok': False,
                'issues': [error_message]
            },
            'trace': []
        }

    def explain_term(self, term, language='cn', threshold=None, max_iterations=None):
        cleaned_term = (term or '').strip()
        threshold = int(threshold or self.pass_score)
        loop_limit = min(int(max_iterations or self.max_iterations), self.max_iterations)
        if not cleaned_term:
            return {
                'term': '',
                'status': 'invalid',
                'passed': False,
                'final_score': 0,
                'error': '术语不能为空'
            }

        language = language or ('cn' if self.rag_service._contains_chinese(cleaned_term) else 'en')
        context = self._build_context(cleaned_term, language)
        if not context['term_docs']:
            return self._fallback_result(cleaned_term, context, '未检索到 MedDRA 候选术语')

        feedback = []
        trace = []
        last_generation = None
        last_judge = None
        last_verifier = None

        for iteration in range(1, loop_limit + 1):
            try:
                if self.generator_mode == 'hybrid':
                    raw_generation, parsed_generation = self._run_hybrid_generator(
                        cleaned_term,
                        context,
                        feedback,
                        iteration
                    )
                else:
                    raw_generation, parsed_generation = self._run_generator(
                        cleaned_term,
                        context['all_docs'],
                        feedback,
                        iteration
                    )
                verifier_result = self._run_verifier(parsed_generation, context['candidate_codes'])
                raw_judge = ''
                if self.use_llm_judge:
                    raw_judge, parsed_judge = self._run_judge(
                        cleaned_term,
                        context['all_docs'],
                        parsed_generation or {'raw_output': raw_generation},
                        threshold
                    )
                else:
                    parsed_judge = self._run_rule_judge(parsed_generation, verifier_result, threshold)
            except Exception as exc:
                current_app.logger.warning(f'MedDRA 解释迭代失败(term={cleaned_term}, iter={iteration}): {exc}')
                return self._fallback_result(cleaned_term, context, f'迭代执行异常: {exc}')

            if not parsed_judge:
                parsed_judge = {
                    'score': 0,
                    'pass': False,
                    'strengths': [],
                    'issues': ['Judge 未返回可解析 JSON'],
                    'must_fix': ['请输出合法 JSON'],
                    'feedback_for_generator': ['请严格输出合法 JSON 并补全必要字段']
                }

            rule_judge = self._run_rule_judge(parsed_generation, verifier_result, threshold)
            if self.use_llm_judge:
                parsed_judge['strengths'] = list(dict.fromkeys((parsed_judge.get('strengths') or []) + (rule_judge.get('strengths') or [])))
                parsed_judge['issues'] = list(dict.fromkeys((parsed_judge.get('issues') or []) + (rule_judge.get('issues') or [])))
                parsed_judge['must_fix'] = list(dict.fromkeys((parsed_judge.get('must_fix') or []) + (rule_judge.get('must_fix') or [])))
                parsed_judge['feedback_for_generator'] = list(dict.fromkeys((parsed_judge.get('feedback_for_generator') or []) + (rule_judge.get('feedback_for_generator') or [])))
                score = min(int(parsed_judge.get('score', 0) or 0), int(rule_judge.get('score', 0) or 0) + 10)
            else:
                score = int(rule_judge.get('score', 0) or 0)
                parsed_judge = rule_judge
            score = max(0, min(score, int(verifier_result.get('score_cap', 100))))
            passed = bool(parsed_judge.get('pass')) and verifier_result.get('ok', False) and score >= threshold
            parsed_judge['score'] = score
            parsed_judge['pass'] = passed

            trace.append({
                'iteration': iteration,
                'generator_raw': raw_generation[:2000],
                'judge_raw': raw_judge[:2000] if raw_judge else '',
                'judge': parsed_judge,
                'verifier': verifier_result
            })

            last_generation = parsed_generation or {'raw_output': raw_generation}
            last_judge = parsed_judge
            last_verifier = verifier_result

            if passed:
                return {
                    'term': cleaned_term,
                    'status': 'passed',
                    'iterations_used': iteration,
                    'passed': True,
                    'final_score': score,
                    'result': last_generation,
                    'judge': last_judge,
                    'verifier': last_verifier,
                    'trace': trace,
                    'sources': self.rag_service._extract_source_docs(context['all_docs'])
                }

            feedback = list(parsed_judge.get('feedback_for_generator') or [])
            feedback.extend(verifier_result.get('issues') or [])

        return {
            'term': cleaned_term,
            'status': 'max_iterations_reached',
            'iterations_used': loop_limit,
            'passed': False,
            'final_score': int((last_judge or {}).get('score', 0)),
            'result': last_generation or {},
            'judge': last_judge or {},
            'verifier': last_verifier or {},
            'trace': trace,
            'sources': self.rag_service._extract_source_docs(context['all_docs'])
        }

    def explain_batch(self, terms, language='cn', threshold=None, max_iterations=None):
        cleaned_terms = []
        for term in terms or []:
            cleaned = str(term or '').strip()
            if cleaned and cleaned not in cleaned_terms:
                cleaned_terms.append(cleaned[:200])

        cleaned_terms = cleaned_terms[:self.max_terms]
        results = [
            self.explain_term(term, language=language, threshold=threshold, max_iterations=max_iterations)
            for term in cleaned_terms
        ]
        passed_count = len([item for item in results if item.get('passed')])
        return {
            'items': results,
            'meta': {
                'batch_size': len(cleaned_terms),
                'passed_count': passed_count,
                'failed_count': len(cleaned_terms) - passed_count,
                'max_iterations': min(int(max_iterations or self.max_iterations), self.max_iterations),
                'pass_score': int(threshold or self.pass_score)
            }
        }
