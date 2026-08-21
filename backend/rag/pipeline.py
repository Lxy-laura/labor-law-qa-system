"""
劳动合同纠纷智能问答系统 - RAG 管线编排（简化版）

简化版说明：
- 不需要 Milvus 向量数据库，仅使用 BM25 检索
- 不需要下载 bge-reranker 模型，使用 BM25 分数排序
- 如果配置了 DeepSeek API Key，使用 API 生成回答
- 如果没有 API Key，使用法条匹配生成回答
"""
import json
import math
import logging
from typing import List, Dict, Any
from config import settings

logger = logging.getLogger(__name__)

class RAGPipeline:
    """RAG 管线编排器（简化版）"""

    def __init__(self):
        self._expander = None
        self._retriever = None
        self._generator = None
        self._landing_service = None
        self._articles = []
        self._bm25_index = None
        self._load_data()

    def _load_data(self):
        """加载法条数据和同义词词典"""
        try:
            # 加载法条
            with open(settings.LEGAL_ARTICLES_PATH, "r", encoding="utf-8") as f:
                self._articles = json.load(f)
            logger.info(f"法条数据加载成功，共 {len(self._articles)} 条")

            # 构建 BM25 索引
            from rank_bm25 import BM25Okapi
            tokenized_docs = [list(art["content"]) for art in self._articles]
            self._bm25_index = BM25Okapi(tokenized_docs)
            logger.info("BM25 索引构建完成")

        except Exception as e:
            logger.warning(f"法条数据加载失败: {e}")
            self._articles = []
            self._bm25_index = None

        try:
            # 加载同义词词典
            with open(settings.SYNONYM_DICT_PATH, "r", encoding="utf-8") as f:
                self._synonym_dict = json.load(f)
            logger.info(f"同义词词典加载成功，共 {len(self._synonym_dict)} 组")
        except Exception as e:
            logger.warning(f"同义词词典加载失败: {e}")
            self._synonym_dict = {}

    def _expand_query(self, query: str) -> str:
        """同义词扩展"""
        expanded_terms = []
        for key, synonyms in self._synonym_dict.items():
            if key in query:
                for syn in synonyms:
                    if syn not in query and syn not in expanded_terms:
                        expanded_terms.append(syn)
        if expanded_terms:
            return f"{query} {' '.join(expanded_terms[:5])}"
        return query

    def _bm25_search(self, query: str, top_k: int = 10) -> List[Dict]:
        """BM25 关键词检索"""
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
        """生成回答：有 API Key 用 DeepSeek，没有则用法条拼接"""
        context_text = "\n\n".join([
            f"[{i+1}] {ctx['law']} {ctx['article']}\n{ctx['content']}"
            for i, ctx in enumerate(contexts)
        ])

        # 尝试使用 DeepSeek API
        if settings.DEEPSEEK_API_KEY and settings.DEEPSEEK_API_KEY != "your_api_key_here":
            try:
                from openai import OpenAI
                client = OpenAI(
                    api_key=settings.DEEPSEEK_API_KEY,
                    base_url=settings.DEEPSEEK_BASE_URL
                )
                system_prompt = (
                    "你是一位专业的劳动合同法律顾问，精通《劳动合同法》及相关劳动法规。"
                    "请基于提供的法条内容，准确、专业地回答用户的劳动合同纠纷问题。"
                    "回答时请：1.明确引用相关法律条文 2.用通俗语言解释 3.给出实用建议"
                )
                user_prompt = f"""请根据以下法律法规内容，回答用户的劳动合同纠纷问题。

【相关法条参考】
{context_text}

【用户问题】
{query}

请准确引用相关法条，用通俗易懂的语言解释法律含义，并给出具体的维权建议。"""

                response = client.chat.completions.create(
                    model=settings.DEEPSEEK_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=2048,
                    temperature=0.3,
                    stream=False
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"DeepSeek API 调用失败: {e}")

        # 无 API Key 时，返回法条匹配结果
        answer_parts = [f"根据您的提问「{query}」，为您检索到以下相关法律条文：\n"]
        for i, ctx in enumerate(contexts[:5], 1):
            answer_parts.append(
                f"{i}. 《{ctx['law']}》{ctx['article']}（{ctx.get('title', '')}）\n"
                f"   {ctx['content']}\n"
            )
        answer_parts.append("\n⚠️ 提示：当前未配置 DeepSeek API Key，以上为法条匹配结果。"
                           "配置 API Key 后可获得 AI 智能解读。")
        return "\n".join(answer_parts)

    def _build_cases(self, query: str) -> List[Dict]:
        """案例推荐"""
        case_templates = [
            {
                "title": "张某诉某科技公司违法解除劳动合同案",
                "summary": "用人单位未依法提前通知即解除劳动合同，法院判决支付双倍经济补偿（赔偿金）。",
                "court": "北京市海淀区人民法院",
                "keywords": ["辞退", "解雇", "开除", "解除", "赔偿", "违法"]
            },
            {
                "title": "李某诉某制造公司试用期违法解除案",
                "summary": "试用期解除劳动合同未证明不符合录用条件，法院认定违法解除，判决支付赔偿金。",
                "court": "上海市浦东新区人民法院",
                "keywords": ["试用期", "试用", "转正", "录用条件"]
            },
            {
                "title": "王某诉某服务公司未签订书面劳动合同案",
                "summary": "用人单位未在一个月内签订书面劳动合同，法院判决支付双倍工资差额。",
                "court": "广州市天河区人民法院",
                "keywords": ["书面合同", "未签", "没签", "双倍工资", "未签订"]
            },
            {
                "title": "赵某诉某建筑公司拖欠工资案",
                "summary": "用人单位长期拖欠工资，劳动者申请支付令后法院判决支付拖欠工资及赔偿金。",
                "court": "深圳市南山区人民法院",
                "keywords": ["工资", "拖欠", "克扣", "欠薪", "不发"]
            },
            {
                "title": "陈某诉某物流公司加班费争议案",
                "summary": "用人单位未依法支付加班费，法院判决支付法定标准的加班费差额。",
                "court": "杭州市余杭区人民法院",
                "keywords": ["加班", "加班费", "工时", "超时"]
            }
        ]

        cases = []
        for template in case_templates:
            if any(kw in query for kw in template["keywords"]):
                cases.append({
                    "title": template["title"],
                    "summary": template["summary"],
                    "court": template["court"]
                })

        if not cases:
            cases.append({
                "title": "张某诉某科技公司违法解除劳动合同案",
                "summary": "用人单位未依法提前通知即解除劳动合同，法院判决支付双倍经济补偿（赔偿金）。",
                "court": "北京市海淀区人民法院"
            })
        return cases

    def _recommend_services(self, query: str) -> List[Dict]:
        """落地服务推荐"""
        services = []

        if any(kw in query for kw in ["工资", "拖欠", "欠薪", "克扣"]):
            services.append({
                "service_type": "工资拖欠维权",
                "hotline": "12333",
                "institution": "当地劳动监察大队",
                "action_guide": [
                    "收集工资条、银行流水、考勤记录等证据",
                    "向用人单位所在地的劳动监察大队投诉",
                    "如投诉无果，向劳动人事争议仲裁委员会申请仲裁",
                    "对仲裁结果不服的，可向人民法院提起诉讼"
                ]
            })
        elif any(kw in query for kw in ["辞退", "解雇", "开除", "解除"]):
            services.append({
                "service_type": "违法解除维权",
                "hotline": "12348",
                "institution": "当地法律援助中心",
                "action_guide": [
                    "保留解除劳动合同通知书、微信聊天记录等证据",
                    "申请劳动仲裁要求支付经济补偿金或赔偿金",
                    "可拨打12348法律援助热线寻求免费法律咨询",
                    "经济困难的可向当地法律援助中心申请免费律师"
                ]
            })
        else:
            services.append({
                "service_type": "劳动争议维权",
                "hotline": "12333",
                "institution": "当地劳动人事争议仲裁委员会",
                "action_guide": [
                    "收集与争议相关的证据材料",
                    "向用人单位所在地的劳动人事争议仲裁委员会申请仲裁",
                    "仲裁时效为一年，从知道权利被侵害之日起计算",
                    "可拨打12333人社热线或12348法援热线咨询"
                ]
            })

        return services

    def run(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """执行完整 RAG 管线"""
        logger.info(f"RAG 管线启动，用户问题: {query}")

        # Step 1: 术语扩展
        expanded_query = self._expand_query(query)
        logger.info(f"[Step 1] 术语扩展: {expanded_query}")

        # Step 2: BM25 检索
        retrieved_docs = self._bm25_search(expanded_query, top_k=20)
        logger.info(f"[Step 2] BM25 检索完成，获取 {len(retrieved_docs)} 条结果")

        # Step 3: 生成回答
        answer = self._generate_answer(query, retrieved_docs)
        logger.info("[Step 3] 回答生成完成")

        # Step 4: 置信度（基于 BM25 分数归一化 + 检索结果数量综合计算）
        # 使用对数缩放，避免 BM25 高分时快速饱和到 0.95
        if retrieved_docs:
            max_score = max(doc.get("score", 0) for doc in retrieved_docs)
            # 用 log1p 压缩分数范围，再映射到 0.55-0.92 区间
            # log1p(40) ≈ 3.7, log1p(10) ≈ 2.4, log1p(5) ≈ 1.8
            # 归一化：log1p(score) / log1p(50) → 0-1 范围
            normalized = math.log1p(max_score) / math.log1p(50)
            # 缩放到 0.55-0.92 区间，保留区分度
            confidence = 0.55 + normalized * 0.37
            # 检索结果数量加成（最多加 0.03）
            hit_bonus = min(len(retrieved_docs) / 20 * 0.03, 0.03)
            confidence = min(confidence + hit_bonus, 0.95)
        else:
            confidence = 0.3

        # Step 5: 构建引用（将 BM25 分数归一化到 0-1 范围）
        citations = []
        if retrieved_docs:
            max_score = max(doc.get("score", 0) for doc in retrieved_docs)
            if max_score <= 0:
                max_score = 1.0
        else:
            max_score = 1.0
        for doc in retrieved_docs[:top_k]:
            citations.append({
                "law": doc.get("law", "劳动合同法"),
                "article": doc.get("article", ""),
                "content": doc.get("content", ""),
                "relevance": round(doc.get("score", 0) / max_score, 4)
            })

        # Step 6: 案例推荐
        cases = self._build_cases(query)

        # Step 7: 落地服务
        landing_services = self._recommend_services(query)

        result = {
            "answer": answer,
            "citations": citations,
            "cases": cases,
            "landing_services": landing_services,
            "confidence": round(confidence, 4),
            "expanded_query": expanded_query
        }

        logger.info("RAG 管线执行完成")
        return result

# 全局单例
_pipeline = None

def get_pipeline() -> RAGPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline()
    return _pipeline