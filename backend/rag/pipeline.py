"""
RAG 管线编排（简化版）
- 不需要 torch / sentence_transformers / Milvus
- 仅使用 BM25 检索
- 有 API Key 用 DeepSeek，没有则返回法条匹配
"""
import json
import logging
from typing import List, Dict, Any
from config import settings

logger = logging.getLogger(__name__)

class RAGPipeline:
    def __init__(self):
        self._articles = []
        self._bm25_index = None
        self._synonym_dict = {}
        self._load_data()

    def _load_data(self):
        try:
            with open(settings.LEGAL_ARTICLES_PATH, "r", encoding="utf-8") as f:
                self._articles = json.load(f)
            from rank_bm25 import BM25Okapi
            tokenized_docs = [list(art["content"]) for art in self._articles]
            self._bm25_index = BM25Okapi(tokenized_docs)
            logger.info(f"法条加载成功 {len(self._articles)} 条, BM25 索引构建完成")
        except Exception as e:
            logger.warning(f"法条加载失败: {e}")
            self._articles = []
            self._bm25_index = None
        try:
            with open(settings.SYNONYM_DICT_PATH, "r", encoding="utf-8") as f:
                self._synonym_dict = json.load(f)
            logger.info(f"同义词词典加载成功 {len(self._synonym_dict)} 组")
        except Exception as e:
            logger.warning(f"同义词词典加载失败: {e}")
            self._synonym_dict = {}

    def _expand_query(self, query: str) -> str:
        expanded = []
        for key, synonyms in self._synonym_dict.items():
            if key in query:
                for syn in synonyms:
                    if syn not in query and syn not in expanded:
                        expanded.append(syn)
        if expanded:
            return f"{query} {' '.join(expanded[:5])}"
        return query

    def _bm25_search(self, query: str, top_k: int = 10) -> List[Dict]:
        if self._bm25_index is None or not self._articles:
            return []
        import numpy as np
        tokenized_query = list(query)
        scores = self._bm25_index.get_scores(tokenized_query)
        top_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_indices:
            if scores[idx] <= 0:
                continue
            art = self._articles[idx]
            results.append({
                "content": art["content"],
                "law": art.get("law", "劳动合同法"),
                "article": art.get("article", ""),
                "title": art.get("title", ""),
                "category": art.get("category", ""),
                "score": float(scores[idx]),
                "rerank_score": float(scores[idx])
            })
        return results

    def _generate_answer(self, query: str, contexts: List[Dict]) -> str:
        context_text = "\n\n".join([
            f"[{i+1}] {ctx['law']} {ctx['article']}\n{ctx['content']}"
            for i, ctx in enumerate(contexts)
        ])
        if settings.DEEPSEEK_API_KEY and settings.DEEPSEEK_API_KEY != "your_api_key_here":
            try:
                from openai import OpenAI
                client = OpenAI(api_key=settings.DEEPSEEK_API_KEY, base_url=settings.DEEPSEEK_BASE_URL)
                response = client.chat.completions.create(
                    model=settings.DEEPSEEK_MODEL,
                    messages=[
                        {"role": "system", "content": "你是专业劳动合同法律顾问，请基于法条准确回答，引用条文，通俗解释，给出建议。"},
                        {"role": "user", "content": f"法条参考：\n{context_text}\n\n用户问题：{query}"}
                    ],
                    max_tokens=2048,
                    temperature=0.3,
                    stream=False
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"DeepSeek API 调用失败: {e}")
        parts = [f"根据您的提问「{query}」，为您检索到以下相关法律条文：\n"]
        for i, ctx in enumerate(contexts[:5], 1):
            parts.append(f"{i}. 《{ctx['law']}》{ctx['article']}（{ctx.get('title', '')}）\n   {ctx['content']}\n")
        parts.append("\n提示：未配置 DeepSeek API Key，以上为法条匹配结果。配置后可获得 AI 智能解读。")
        return "\n".join(parts)

    def _build_cases(self, query: str) -> List[Dict]:
        templates = [
            {"title": "张某诉某科技公司违法解除劳动合同案", "summary": "用人单位未依法提前通知即解除劳动合同，法院判决支付双倍经济补偿。", "court": "北京市海淀区人民法院", "keywords": ["辞退", "解雇", "开除", "解除", "赔偿", "违法"]},
            {"title": "李某诉某制造公司试用期违法解除案", "summary": "试用期解除未证明不符合录用条件，法院认定违法解除，判决支付赔偿金。", "court": "上海市浦东新区人民法院", "keywords": ["试用期", "试用", "转正", "录用条件"]},
            {"title": "王某诉某服务公司未签订书面劳动合同案", "summary": "未在一个月内签订书面劳动合同，法院判决支付双倍工资差额。", "court": "广州市天河区人民法院", "keywords": ["书面合同", "未签", "没签", "双倍工资"]},
            {"title": "赵某诉某建筑公司拖欠工资案", "summary": "长期拖欠工资，法院判决支付拖欠工资及赔偿金。", "court": "深圳市南山区人民法院", "keywords": ["工资", "拖欠", "克扣", "欠薪", "不发"]},
            {"title": "陈某诉某物流公司加班费争议案", "summary": "未依法支付加班费，法院判决支付加班费差额。", "court": "杭州市余杭区人民法院", "keywords": ["加班", "加班费", "工时", "超时"]}
        ]
        cases = []
        for t in templates:
            if any(kw in query for kw in t["keywords"]):
                cases.append({"title": t["title"], "summary": t["summary"], "court": t["court"]})
        if not cases:
            cases.append({"title": templates[0]["title"], "summary": templates[0]["summary"], "court": templates[0]["court"]})
        return cases

    def _recommend_services(self, query: str) -> List[Dict]:
        if any(kw in query for kw in ["工资", "拖欠", "欠薪", "克扣"]):
            return [{"service_type": "工资拖欠维权", "hotline": "12333", "institution": "当地劳动监察大队", "action_guide": ["收集工资条、银行流水、考勤记录等证据", "向劳动监察大队投诉", "如投诉无果申请劳动仲裁", "对仲裁结果不服可向法院起诉"]}]
        elif any(kw in query for kw in ["辞退", "解雇", "开除", "解除"]):
            return [{"service_type": "违法解除维权", "hotline": "12348", "institution": "当地法律援助中心", "action_guide": ["保留解除通知书、聊天记录等证据", "申请劳动仲裁要求支付赔偿金", "拨打12348法援热线咨询", "经济困难可申请免费律师"]}]
        else:
            return [{"service_type": "劳动争议维权", "hotline": "12333", "institution": "当地劳动人事争议仲裁委员会", "action_guide": ["收集相关证据材料", "向劳动仲裁委申请仲裁", "仲裁时效一年", "可拨打12333或12348咨询"]}]

    def run(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        expanded_query = self._expand_query(query)
        retrieved_docs = self._bm25_search(expanded_query, top_k=20)
        answer = self._generate_answer(query, retrieved_docs)
        confidence = 0.85 if retrieved_docs else 0.3
        if retrieved_docs:
            max_score = max(doc.get("score", 0) for doc in retrieved_docs)
            confidence = min(0.3 + max_score / 10, 0.95)
        citations = [{"law": d.get("law", "劳动合同法"), "article": d.get("article", ""), "content": d.get("content", ""), "relevance": round(d.get("score", 0), 4)} for d in retrieved_docs[:top_k]]
        cases = self._build_cases(query)
        landing_services = self._recommend_services(query)
        return {"answer": answer, "citations": citations, "cases": cases, "landing_services": landing_services, "confidence": round(confidence, 4), "expanded_query": expanded_query}

_pipeline = None

def get_pipeline() -> RAGPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline()
    return _pipeline