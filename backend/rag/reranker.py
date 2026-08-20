"""
劳动合同纠纷智能问答系统 - Cross-Encoder 重排序器

使用 BAAI/bge-reranker-base 模型对混合检索结果进行重排序。
Cross-Encoder 与 Bi-Encoder 不同，它将查询和文档拼接后一起输入模型，
能更精确地计算查询与文档的相关性分数。

流程:
1. 将查询与每个候选文档组成 (query, document) 对
2. 使用 Cross-Encoder 计算每对的相关性分数
3. 按分数降序排列，返回 Top-K
"""
import logging
from typing import List, Dict, Any
from config import settings

logger = logging.getLogger(__name__)


class Reranker:
    """
    Cross-Encoder 重排序器

    使用 BAAI/bge-reranker-base 对检索结果重新打分排序，
    比向量检索的相似度分数更精确
    """

    def __init__(self):
        """初始化 Cross-Encoder 重排序模型"""
        from sentence_transformers import CrossEncoder

        logger.info(f"正在加载重排序模型: {settings.RERANKER_MODEL}")
        self.model = CrossEncoder(settings.RERANKER_MODEL)
        logger.info("重排序模型加载完成")

    def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        对检索结果进行重排序

        参数:
            query: 用户查询文本
            documents: 检索结果列表（来自 HybridRetriever）
            top_k: 重排序后返回的文档数量

        返回:
            重排序后的 Top-K 文档列表，每个文档增加 rerank_score 字段
        """
        if not documents:
            logger.warning("无文档需要重排序")
            return []

        # 构建查询-文档对
        pairs = [(query, doc["content"]) for doc in documents]

        # 使用 Cross-Encoder 计算相关性分数
        scores = self.model.predict(pairs)

        # 将重排序分数附加到文档
        for doc, score in zip(documents, scores):
            doc["rerank_score"] = float(score)

        # 按重排序分数降序排列
        reranked = sorted(documents, key=lambda x: x["rerank_score"], reverse=True)

        # 取 Top-K
        top_results = reranked[:top_k]

        logger.info(f"重排序完成: 输入 {len(documents)} 条, 输出 {len(top_results)} 条")
        return top_results


# 全局单例
_reranker = None


def get_reranker() -> Reranker:
    """获取全局 Reranker 单例实例"""
    global _reranker
    if _reranker is None:
        _reranker = Reranker()
    return _reranker
