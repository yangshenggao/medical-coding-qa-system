"""
RAG问答核心服务
支持通用知识库问答，以及 WHODrug / MedDRA 词典问答
"""
import re

from flask import current_app
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_ollama import ChatOllama

from models import db
from models.meddra import MeddraTerm
from models.whodrug import WhodrugDrug
from services.vector_service import VectorService
MEDDRA_RAG_FALLBACK_LEVELS = ['SOC', 'HLGT', 'HLT', 'PT']

GENERAL_SYSTEM_PROMPTS = {
    'cn': """你是一个医学编码智能助手。请严格基于参考资料回答。

要求：
1. 只能根据参考资料作答，不要编造不存在的编码或层级
2. 如果证据不足，要明确说明“仅供候选参考，需人工复核”
3. 回答使用中文
4. 回答尽量结构化，优先给出编码、术语/药物名称、理由

参考资料：
{context}
""",
    'en': """You are a medical coding assistant. Answer strictly based on the provided references.

Requirements:
1. Only answer from the references and do not invent codes or hierarchies
2. If evidence is insufficient, explicitly say the result is for candidate reference only and needs manual review
3. Answer in English
4. Keep the answer structured and prioritize code, term/drug name, and rationale

References:
{context}
"""
}

WHODRUG_SYSTEM_PROMPTS = {
    'cn': """你是 WHODrug 药物编码助手。请仅根据提供的 WHODrug 检索结果回答。

输出要求：
1. 优先返回最相关药物的 Drug Code、MPID、药物名称、ATC
2. 如果用户描述不够精确，说明这是候选结果，需要人工确认
3. 不要虚构药品或编码

参考资料：
{context}
""",
    'en': """You are a WHODrug coding assistant. Answer only from the provided WHODrug search results.

Requirements:
1. Prioritize the most relevant drug records with Drug Code, MPID, drug name, and ATC
2. If the user's description is not specific enough, state clearly that the results are candidates and require manual confirmation
3. Do not invent drugs or codes

References:
{context}
"""
}

MEDDRA_SYSTEM_PROMPTS = {
    'cn': """你是 MedDRA 术语编码助手。请仅根据提供的 MedDRA 候选术语回答。

输出要求：
1. 优先推荐最可能匹配的 1-3 个术语
2. 每个术语给出代码、名称、层级，并简述为什么匹配
3. 若用户给的是影像描述/口语表达，请明确说明属于语义推荐，需人工医学编码复核
4. 不要虚构术语或代码

参考资料：
{context}
""",
    'en': """You are a MedDRA coding assistant. Answer only from the provided MedDRA candidate terms.

Requirements:
1. Prioritize the 1-3 most likely matching terms
2. For each term, provide code, name, level, and a brief reason why it matches
3. If the user input is an imaging description or colloquial expression, clearly mark it as a semantic recommendation requiring manual medical coding review
4. Do not invent terms or codes

References:
{context}
"""
}

MEDDRA_GUIDANCE_SYSTEM_PROMPTS = {
    'cn': """你是 MedDRA 编码辅助助手。请同时参考术语候选结果与 MedDRA 规则说明文档回答。

输出要求：
1. 先给出最可能的 1-3 个候选 PT/LLT，并说明层级
2. 结合规则说明解释为什么推荐这些术语，而不是直接编造结论
3. 如果规则文档只提供一般原则，要明确说明“规则参考”与“候选术语”分别来自哪里
4. 若证据不足，必须提示“仅供候选参考，需人工复核”
5. 不要输出未在候选结果或规则文档中出现的术语/编码

参考资料：
{context}
""",
    'en': """You are a MedDRA coding support assistant. Answer by combining candidate terms and MedDRA guidance documents.

Requirements:
1. First provide the 1-3 most likely PT/LLT candidates and explain their hierarchy
2. Use the guidance documents to explain why those terms are recommended instead of inventing conclusions
3. If the guidance only provides general rules, clearly separate the rule-based references from the candidate terms
4. If evidence is insufficient, explicitly say the results are for candidate reference only and require manual review
5. Do not output terms or codes that do not appear in the candidate results or guidance documents

References:
{context}
"""
}


class RAGService:
    """RAG问答服务类"""

    def __init__(self):
        self.llm = ChatOllama(
            model=current_app.config['OLLAMA_LLM_MODEL'],
            base_url=current_app.config['OLLAMA_BASE_URL'],
            temperature=0.2,
            timeout=3600
        )
        self.vector_service = VectorService()

    def _build_chain(self, system_prompt):
        prompt = ChatPromptTemplate.from_messages([
            ('system', system_prompt),
            ('human', '{question}')
        ])
        return prompt | self.llm | StrOutputParser()

    def _format_docs(self, docs):
        formatted = []
        for i, doc in enumerate(docs, 1):
            source = doc.get('source', '未知来源')
            content = doc.get('content', '')
            formatted.append(f"[来源{i}: {source}]\n{content}")
        return '\n\n'.join(formatted)

    def _extract_source_docs(self, docs):
        source_docs = []
        for doc in docs[:5]:
            source_docs.append({
                'file_name': doc.get('source', '未知来源'),
                'content': doc.get('content', '')[:200]
            })
        return source_docs

    def _tokenize_question(self, question):
        tokens = re.split(r'[\s,，。;；:：/\\()（）]+', question)
        tokens = [token.strip() for token in tokens if len(token.strip()) >= 2]
        return tokens[:8]

    def _contains_chinese(self, text):
        return bool(re.search(r'[\u4e00-\u9fff]', text or ''))

    def _detect_language(self, text):
        return 'cn' if self._contains_chinese(text) else 'en'

    def _normalize_dictionary_question(self, question, language):
        cleaned = (question or '').strip()
        if not cleaned:
            return ''

        tokens = re.split(r'[\s,，。;；:：/\\()（）]+', cleaned)
        normalized_tokens = []
        noise_tokens = {
            'cn', 'zh', 'zh-cn', 'en', 'en-us', 'english', 'chinese',
            'term', 'code', 'pt', 'llt', 'hlt', 'hlgt', 'soc',
            'meddra', 'whodrug'
        }

        for token in tokens:
            token = token.strip()
            if not token:
                continue
            token_lower = token.lower()
            if token_lower in noise_tokens:
                continue
            normalized_tokens.append(token)

        normalized = ' '.join(normalized_tokens).strip()
        return normalized or cleaned

    def _build_meddra_conditions(self, question):
        tokens = self._tokenize_question(question)
        conditions = []
        for token in [question] + tokens:
            pattern = f'%{token}%'
            conditions.append(MeddraTerm.name.like(pattern))
            conditions.append(MeddraTerm.code.like(pattern))
        return conditions

    def _meddra_match_rank(self, row, question):
        normalized = (question or '').strip().lower()
        name = (row.name or '').lower()
        code = (row.code or '').lower()
        if normalized and (name == normalized or code == normalized):
            return 0
        if normalized and (name.startswith(normalized) or code.startswith(normalized)):
            return 1
        if normalized and normalized in name:
            return 2
        return 3

    def _ordered_meddra_keyword_rows(self, question, language, levels):
        conditions = self._build_meddra_conditions(question)
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
            level_rows.sort(key=lambda item: (self._meddra_match_rank(item, question), item.name))
            for row in level_rows:
                if row.code in seen_codes:
                    continue
                seen_codes.add(row.code)
                rows.append(row)
        return rows

    def _ask_with_docs(self, question, docs, system_prompt, language):
        if not docs:
            if language == 'en':
                return 'Sorry, there is not enough reference material available to provide a reliable coding suggestion right now.', []
            return '抱歉，当前没有检索到足够的参考资料，暂时无法给出可靠编码建议。', []

        chain = self._build_chain(system_prompt)
        answer = chain.invoke({
            'context': self._format_docs(docs),
            'question': question
        })
        return answer, self._extract_source_docs(docs)

    def _search_whodrug_docs(self, question, language, limit=8):
        normalized_question = self._normalize_dictionary_question(question, language)
        tokens = self._tokenize_question(normalized_question)
        conditions = []
        for token in [normalized_question] + tokens:
            pattern = f'%{token}%'
            conditions.append(WhodrugDrug.drug_name.like(pattern))
            conditions.append(WhodrugDrug.drug_code.like(pattern))
            conditions.append(WhodrugDrug.mpid.like(pattern))
            conditions.append(WhodrugDrug.atc_code.like(pattern))

        query = WhodrugDrug.query.filter_by(language=language)
        if conditions:
            query = query.filter(db.or_(*conditions))

        rows = query.order_by(WhodrugDrug.drug_name.asc()).limit(limit).all()
        docs = []
        for row in rows:
            if language == 'en':
                content = '\n'.join(filter(None, [
                    f'Drug Name: {row.drug_name}',
                    f'Drug Code: {row.drug_code}',
                    f'MPID: {row.mpid}' if row.mpid else '',
                    f'Active Ingredient: {row.substance_name}' if row.substance_name else '',
                    f'ATC: {row.atc_code}' if row.atc_code else '',
                    f'Pharmaceutical Form: {row.pharmaceutical_form}' if row.pharmaceutical_form else '',
                    f'Country: {row.country}' if row.country else '',
                    f'MAH: {row.mah}' if row.mah else ''
                ]))
            else:
                content = '\n'.join(filter(None, [
                    f'药物名称: {row.drug_name}',
                    f'Drug Code: {row.drug_code}',
                    f'MPID: {row.mpid}' if row.mpid else '',
                    f'活性成分: {row.substance_name}' if row.substance_name else '',
                    f'ATC: {row.atc_code}' if row.atc_code else '',
                    f'剂型: {row.pharmaceutical_form}' if row.pharmaceutical_form else '',
                    f'国家: {row.country}' if row.country else '',
                    f'上市许可持有人: {row.mah}' if row.mah else ''
                ]))
            docs.append({
                'source': f'WHODrug/{row.drug_code}',
                'content': content
            })
        return docs

    def _search_meddra_docs(self, question, limit=8):
        language = self._detect_language(question)
        normalized_question = self._normalize_dictionary_question(question, language)
        keyword_rows = self._ordered_meddra_keyword_rows(normalized_question, language, ['PT'])
        if not keyword_rows:
            keyword_rows = self._ordered_meddra_keyword_rows(
                normalized_question, language, MEDDRA_RAG_FALLBACK_LEVELS
            )

        merged = {}
        docs = []
        for row in keyword_rows:
            merged[row.code] = True
            if language == 'en':
                content = '\n'.join(filter(None, [
                    f'Term Name: {row.name}',
                    f'Code: {row.code}',
                    f'Level: {row.term_level}',
                    f'Parent Code: {row.parent_code}' if row.parent_code else '',
                    f'SOC Code: {row.soc_code}' if row.soc_code else ''
                ]))
            else:
                content = '\n'.join(filter(None, [
                    f'术语名称: {row.name}',
                    f'代码: {row.code}',
                    f'层级: {row.term_level}',
                    f'父级代码: {row.parent_code}' if row.parent_code else '',
                    f'SOC代码: {row.soc_code}' if row.soc_code else ''
                ]))
            docs.append({
                'source': f'MedDRA/{row.term_level}/{row.code}',
                'content': content
            })
            if len(docs) >= limit:
                return docs[:limit]

        try:
            semantic_rows = self.vector_service.search_collection(
                f'meddra_{language}', normalized_question, top_k=limit
            )
        except Exception:
            semantic_rows = []

        for doc, score in semantic_rows:
            code = doc.metadata.get('code', '')
            if code in merged:
                continue
            if language == 'en':
                content = '\n'.join(filter(None, [
                    f"Term Name: {doc.metadata.get('name', doc.page_content)}",
                    f"Code: {code}",
                    f"Level: {doc.metadata.get('level', '')}",
                    f"Parent Code: {doc.metadata.get('parent_code', '')}" if doc.metadata.get('parent_code') else '',
                    f"SOC: {doc.metadata.get('soc_name', '')}" if doc.metadata.get('soc_name') else '',
                    f"Similarity Reference: {max(0, 1 - float(score)):.3f}"
                ]))
            else:
                content = '\n'.join(filter(None, [
                    f"术语名称: {doc.metadata.get('name', doc.page_content)}",
                    f"代码: {code}",
                    f"层级: {doc.metadata.get('level', '')}",
                    f"父级代码: {doc.metadata.get('parent_code', '')}" if doc.metadata.get('parent_code') else '',
                    f"SOC: {doc.metadata.get('soc_name', '')}" if doc.metadata.get('soc_name') else '',
                    f"相似度参考: {max(0, 1 - float(score)):.3f}"
                ]))
            docs.append({
                'source': f"MedDRA/{doc.metadata.get('level', '')}/{code}",
                'content': content
            })
            merged[code] = True

        return docs[:limit]

    def _search_meddra_guidance_docs(self, question, language, limit=4):
        normalized_question = self._normalize_dictionary_question(question, language)
        try:
            guidance_rows = self.vector_service.search_collection(
                f'meddra_guidance_{language}',
                query=normalized_question,
                top_k=limit
            )
        except Exception:
            guidance_rows = []

        docs = []
        for doc, score in guidance_rows:
            if language == 'en':
                content = '\n'.join(filter(None, [
                    f"Title: {doc.metadata.get('title', '')}" if doc.metadata.get('title') else '',
                    doc.page_content,
                    f"Similarity Reference: {max(0, 1 - float(score)):.3f}"
                ]))
            else:
                content = '\n'.join(filter(None, [
                    f"标题: {doc.metadata.get('title', '')}" if doc.metadata.get('title') else '',
                    doc.page_content,
                    f"相似度参考: {max(0, 1 - float(score)):.3f}"
                ]))
            docs.append({
                'source': f"MedDRA指南/{doc.metadata.get('source', '未知文档')}",
                'content': content
            })
        return docs

    def _ask_dictionary(self, question, kb_name):
        kb_name_lower = (kb_name or '').lower()
        language = self._detect_language(question)
        if kb_name_lower == 'whodrug词典':
            docs = self._search_whodrug_docs(question, language)
            if not docs:
                if language == 'en':
                    return 'No matching WHODrug records were found. Please try a more precise drug name, Drug Code, MPID, or active ingredient.', []
                return '未检索到匹配的 WHODrug 药物记录，请尝试输入更准确的药品名、Drug Code、MPID 或活性成分。', []
            return self._ask_with_docs(question, docs, WHODRUG_SYSTEM_PROMPTS[language], language)

        if kb_name_lower == 'meddra词典':
            term_docs = self._search_meddra_docs(question)
            if not term_docs:
                if language == 'en':
                    return 'No matching MedDRA terms were found. Please try using a more standard symptom, diagnosis, or imaging description.', []
                return '未检索到匹配的 MedDRA 术语，请尝试使用更标准的症状、诊断或影像学描述。', []
            guidance_docs = self._search_meddra_guidance_docs(question, language)
            docs = term_docs + guidance_docs
            system_prompt = MEDDRA_GUIDANCE_SYSTEM_PROMPTS[language] if guidance_docs else MEDDRA_SYSTEM_PROMPTS[language]
            return self._ask_with_docs(question, docs, system_prompt, language)

        return None

    def ask(self, question, kb_id, kb_name=''):
        dictionary_result = self._ask_dictionary(question, kb_name)
        if dictionary_result:
            return dictionary_result

        retriever = self.vector_service.get_retriever(kb_id)
        docs = retriever.invoke(question)

        if not docs:
            if self._detect_language(question) == 'en':
                return 'Sorry, no relevant content was found in the knowledge base. Please try rephrasing your question.', []
            return '抱歉，在知识库中未找到与您问题相关的内容，请尝试换个方式提问。', []

        formatted_docs = []
        for doc in docs:
            formatted_docs.append({
                'source': doc.metadata.get('file_name', '未知来源'),
                'content': doc.page_content
            })
        language = self._detect_language(question)
        return self._ask_with_docs(question, formatted_docs, GENERAL_SYSTEM_PROMPTS[language], language)
