"""
劳动合同纠纷智能问答系统 - RAG 管线编排

完整 RAG 管线流程：
1. 术语扩展（SynonymExpander）- 将用户查询扩展为包含同义词的查询
2. 混合检索（HybridRetriever）- Milvus 向量检索 Top20 + BM25 Top20 → RRF 融合
3. 重排序（Reranker）- Cross-Encoder 对融合结果重新打分排序
4. 生成（Generator）- 调用 DeepSeek API 基于重排序结果生成回答
5. 置信度计算 - 基于重排序分数和检索结果数量计算回答置信度
6. 落地服务推荐 - 根据问题类型推荐维权热线和行动指引
"""
import math
import logging
from typing import List, Dict, Any
from config import settings

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    RAG 管线编排器

    将术语扩展、混合检索、重排序、生成、置信度计算和落地服务推荐
    有序组合，提供端到端的问答能力
    """

    def __init__(self):
        """初始化 RAG 管线（延迟加载各组件）"""
        self._expander = None
        self._retriever = None
        self._reranker = None
        self._generator = None
        self._landing_service = None

    # ========== 延迟加载各组件（使用全局单例）==========

    @property
    def expander(self):
        """同义词扩展器（延迟加载）"""
        if self._expander is None:
            from rag.synonym_expander import get_expander
            self._expander = get_expander()
        return self._expander

    @property
    def retriever(self):
        """混合检索器（延迟加载）"""
        if self._retriever is None:
            from rag.retriever import get_retriever
            self._retriever = get_retriever()
        return self._retriever

    @property
    def reranker(self):
        """重排序器（延迟加载）"""
        if self._reranker is None:
            from rag.reranker import get_reranker
            self._reranker = get_reranker()
        return self._reranker

    @property
    def generator(self):
        """回答生成器（延迟加载）"""
        if self._generator is None:
            from rag.generator import get_generator
            self._generator = get_generator()
        return self._generator

    @property
    def landing_service(self):
        """落地服务推荐器（延迟加载）"""
        if self._landing_service is None:
            from services.landing import LandingService
            self._landing_service = LandingService()
        return self._landing_service

    def run(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        执行完整 RAG 管线

        参数:
            query: 用户问题
            top_k: 最终返回的文档引用数量

        返回:
            包含以下字段的字典:
            - answer: 回答文本
            - citations: 法条引用列表
            - cases: 案例参考列表
            - landing_services: 落地服务列表
            - confidence: 置信度（0-1）
            - expanded_query: 扩展后的查询
        """
        logger.info(f"RAG 管线启动，用户问题: {query}")

        # ========== Step 1: 术语扩展 ==========
        # 将用户查询扩展为包含同义词的查询，提升检索召回率
        expanded_query = self.expander.expand(query)
        logger.info(f"[Step 1] 术语扩展完成: {expanded_query}")

        # ========== Step 2: 混合检索 ==========
        # 向量检索 Top20 + BM25 Top20 → RRF 融合
        retrieved_docs = self.retriever.retrieve(expanded_query)
        logger.info(f"[Step 2] 混合检索完成，获取 {len(retrieved_docs)} 条候选结果")

        # ========== Step 3: 重排序 ==========
        # Cross-Encoder 对候选结果重新打分排序
        reranked_docs = self.reranker.rerank(
            query,
            retrieved_docs,
            top_k=max(top_k, settings.RERANK_TOP_K)
        )
        logger.info(f"[Step 3] 重排序完成，获取 {len(reranked_docs)} 条精确结果")

        # ========== Step 4: 生成回答 ==========
        # 调用 DeepSeek API，基于重排序后的法条上下文生成回答
        answer = self.generator.generate(query, reranked_docs)
        logger.info(f"[Step 4] 回答生成完成")

        # ========== Step 5: 置信度计算 ==========
        # 基于重排序分数和检索结果数量计算置信度
        confidence = self._calculate_confidence(reranked_docs, retrieved_docs)
        logger.info(f"[Step 5] 置信度: {confidence}")

        # ========== Step 6: 构建法条引用 ==========
        citations = self._build_citations(reranked_docs[:top_k])

        # ========== Step 7: 案例参考 ==========
        cases = self._build_cases(query)

        # ========== Step 8: 落地服务推荐 ==========
        landing_services = self.landing_service.recommend(query)

        # 组装最终结果
        result = {
            "answer": answer,
            "citations": citations,
            "cases": cases,
            "landing_services": landing_services,
            "confidence": confidence,
            "expanded_query": expanded_query
        }

        logger.info("RAG 管线执行完成")
        return result

    def _calculate_confidence(
        self,
        reranked_docs: List[Dict],
        retrieved_docs: List[Dict]
    ) -> float:
        """
        计算回答置信度

        策略:
        1. 取重排序最高分，使用 sigmoid 归一化到 0-1
        2. 如果有足够多的检索结果，适当提升置信度
        3. 限制在合理范围 [0.3, 0.98]

        参数:
            reranked_docs: 重排序后的文档列表
            retrieved_docs: 融合检索的文档列表

        返回:
            置信度（0-1 之间的浮点数）
        """
        if not reranked_docs:
            return 0.3

        # 取重排序最高分
        max_rerank_score = max([
            doc.get("rerank_score", 0) for doc in reranked_docs
        ])

        # 使用 sigmoid 归一化（Cross-Encoder 分数范围不固定）
        confidence = 1.0 / (1.0 + math.exp(-max_rerank_score))

        # 有足够多的检索结果时提升置信度
        if len(reranked_docs) >= 3:
            confidence = min(confidence + 0.1, 0.95)

        # 限制在合理范围
        confidence = max(0.3, min(confidence, 0.98))

        return round(confidence, 4)

    def _build_citations(self, docs: List[Dict]) -> List[Dict[str, Any]]:
        """
        构建法条引用列表

        参数:
            docs: 重排序后的文档列表

        返回:
            引用列表，每项包含 law, article, content, relevance
        """
        citations = []
        for doc in docs:
            citations.append({
                "law": doc.get("law", "劳动合同法"),
                "article": doc.get("article", ""),
                "content": doc.get("content", ""),
                "relevance": round(
                    doc.get("rerank_score", doc.get("rrf_score", 0)), 4
                )
            })
        return citations

    def _build_cases(self, query: str) -> List[Dict[str, Any]]:
        """
        根据查询内容构建案例参考

        基于查询关键词匹配预设的典型案例模板

        参数:
            query: 用户查询

        返回:
            案例列表，每项包含 title, summary, court
        """
        cases = []

        # 预设典型案例模板
        case_templates = [
            {
                "title": "张某诉某科技公司违法解除劳动合同案",
                "summary": "用人单位未依法提前通知即解除劳动合同，"
                          "法院判决支付双倍经济补偿（赔偿金）。",
                "court": "北京市海淀区人民法院",
                "keywords": ["辞退", "解雇", "开除", "解除", "赔偿", "违法"]
            },
            {
                "title": "李某诉某制造公司试用期违法解除案",
                "summary": "试用期解除劳动合同未证明不符合录用条件，"
                          "法院认定违法解除，判决支付赔偿金。",
                "court": "上海市浦东新区人民法院",
                "keywords": ["试用期", "试用", "转正", "录用条件"]
            },
            {
                "title": "王某诉某服务公司未签订书面劳动合同案",
                "summary": "用人单位未在一个月内签订书面劳动合同，"
                          "法院判决支付双倍工资差额。",
                "court": "广州市天河区人民法院",
                "keywords": ["书面合同", "未签", "没签", "双倍工资", "未签订"]
            },
            {
                "title": "赵某诉某建筑公司拖欠工资案",
                "summary": "用人单位长期拖欠工资，劳动者申请支付令后"
                          "法院判决支付拖欠工资及赔偿金。",
                "court": "深圳市南山区人民法院",
                "keywords": ["工资", "拖欠", "克扣", "欠薪", "不发"]
            },
            {
                "title": "陈某诉某物流公司加班费争议案",
                "summary": "用人单位未依法支付加班费，"
                          "法院判决支付法定标准的加班费差额。",
                "court": "杭州市余杭区人民法院",
                "keywords": ["加班", "加班费", "工时", "超时"]
            }
        ]

        # 根据查询内容匹配案例
        for template in case_templates:
            if any(kw in query for kw in template["keywords"]):
                cases.append({
                    "title": template["title"],
                    "summary": template["summary"],
                    "court": template["court"]
                })

        # 如果没有匹配到任何案例，返回通用案例
        if not cases:
            cases.append({
                "title": "张某诉某科技公司违法解除劳动合同案",
                "summary": "用人单位未依法提前通知即解除劳动合同，"
                          "法院判决支付双倍经济补偿（赔偿金）。",
                "court": "北京市海淀区人民法院"
            })

        return cases


# 全局单例
_pipeline = None


def get_pipeline() -> RAGPipeline:
    """获取全局 RAGPipeline 单例实例"""
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline()
    return _pipeline
