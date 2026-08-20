"""
劳动合同纠纷智能问答系统 - 混合检索器

实现混合检索策略：
1. Milvus 向量检索 - 语义相似性，返回 Top20
2. BM25 关键词检索 - 词频匹配，返回 Top20
3. RRF（Reciprocal Rank Fusion）融合 - 合并两路结果

RRF 公式: score(d) = Σ 1/(k + rank_i(d))
其中 k 为融合常数（默认60），rank_i(d) 为文档在第 i 路检索中的排名
"""
import json
import logging
import numpy as np
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
from config import settings

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    混合检索器

    结合 Milvus 向量检索和 BM25 关键词检索，
    使用 RRF 融合两路结果，兼顾语义匹配和关键词匹配
    """

    def __init__(self):
        """初始化混合检索器"""
        self.collection = None        # Milvus 集合
        self.bm25_index = None        # BM25 索引
        self.documents = []           # BM25 索引的文档内容列表
        self.doc_metadata = []        # 文档元数据列表

        # 连接 Milvus 向量数据库
        self._connect_milvus()

        # 加载法律法条数据构建 BM25 索引
        self._load_legal_articles()

    def _connect_milvus(self):
        """连接 Milvus 向量数据库，如果集合不存在则创建"""
        try:
            from pymilvus import (
                connections, Collection, utility,
                FieldSchema, CollectionSchema, DataType
            )

            # 建立连接
            connections.connect(
                alias="default",
                host=settings.MILVUS_HOST,
                port=settings.MILVUS_PORT
            )
            logger.info("Milvus 连接成功")

            # 检查集合是否存在，不存在则创建
            if not utility.has_collection(settings.MILVUS_COLLECTION):
                self._create_collection()

            # 加载集合到内存
            self.collection = Collection(settings.MILVUS_COLLECTION)
            self.collection.load()
            logger.info(f"Milvus 集合 '{settings.MILVUS_COLLECTION}' 已加载")

        except Exception as e:
            logger.warning(f"Milvus 连接失败，将仅使用 BM25 检索: {e}")
            self.collection = None

    def _create_collection(self):
        """创建 Milvus 集合（包含向量字段和元数据字段）"""
        from pymilvus import FieldSchema, CollectionSchema, DataType, Collection

        fields = [
            # 主键（自增）
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            # 向量字段
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=settings.MILVUS_DIMENSION),
            # 文档内容
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=2000),
            # 所属文档ID
            FieldSchema(name="doc_id", dtype=DataType.INT64),
            # 来源标识
            FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=500),
        ]
        schema = CollectionSchema(fields, description="劳动合同法律文档向量集合")
        Collection(settings.MILVUS_COLLECTION, schema)

        # 创建 IVF_FLAT 索引
        collection = Collection(settings.MILVUS_COLLECTION)
        collection.create_index(
            field_name="embedding",
            index_params={
                "metric_type": "IP",          # 内积（配合 L2 归一化等价于余弦相似度）
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128}
            }
        )
        logger.info(f"Milvus 集合 '{settings.MILVUS_COLLECTION}' 及索引创建成功")

    def _load_legal_articles(self):
        """加载法律法条数据，用于构建 BM25 索引"""
        try:
            with open(settings.LEGAL_ARTICLES_PATH, "r", encoding="utf-8") as f:
                articles = json.load(f)

            self.documents = [art["content"] for art in articles]
            self.doc_metadata = articles

            # 构建中文 BM25 索引（按字符切分）
            tokenized_docs = [list(doc) for doc in self.documents]
            self.bm25_index = BM25Okapi(tokenized_docs)
            logger.info(f"BM25 索引构建完成，共 {len(self.documents)} 条法条")

        except Exception as e:
            logger.warning(f"法律法条数据加载失败: {e}")
            self.documents = []
            self.doc_metadata = []
            self.bm25_index = None

    def vector_search(self, query: str, top_k: int = 20) -> List[Dict[str, Any]]:
        """
        Milvus 向量检索

        参数:
            query: 查询文本
            top_k: 返回结果数量

        返回:
            检索结果列表，每项包含 content, score, rank
        """
        if self.collection is None:
            logger.warning("Milvus 未连接，跳过向量检索")
            return []

        try:
            from rag.embedder import get_embedder

            # 编码查询
            embedder = get_embedder()
            query_vec = embedder.encode_query(query)

            # 执行向量检索
            results = self.collection.search(
                data=[query_vec.tolist()],
                anns_field="embedding",
                param={
                    "metric_type": "IP",
                    "params": {"nprobe": 10}
                },
                limit=top_k,
                output_fields=["content", "doc_id", "source"]
            )

            # 解析结果
            search_results = []
            for hit in results[0]:
                entity = hit.entity
                search_results.append({
                    "content": entity.get("content", ""),
                    "doc_id": entity.get("doc_id", 0),
                    "source": entity.get("source", ""),
                    "score": float(hit.score),
                    "rank": len(search_results) + 1
                })

            logger.info(f"向量检索完成，返回 {len(search_results)} 条结果")
            return search_results

        except Exception as e:
            logger.error(f"向量检索失败: {e}")
            return []

    def bm25_search(self, query: str, top_k: int = 20) -> List[Dict[str, Any]]:
        """
        BM25 关键词检索

        参数:
            query: 查询文本
            top_k: 返回结果数量

        返回:
            检索结果列表，每项包含 content, law, article, score, rank
        """
        if self.bm25_index is None or not self.documents:
            logger.warning("BM25 索引未就绪，跳过关键词检索")
            return []

        # 中文按字符切分
        tokenized_query = list(query)
        scores = self.bm25_index.get_scores(tokenized_query)

        # 获取 Top-K 结果
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            if scores[idx] <= 0:
                continue
            meta = self.doc_metadata[idx] if idx < len(self.doc_metadata) else {}
            results.append({
                "content": self.documents[idx],
                "law": meta.get("law", ""),
                "article": meta.get("article", ""),
                "title": meta.get("title", ""),
                "category": meta.get("category", ""),
                "score": float(scores[idx]),
                "rank": len(results) + 1
            })

        logger.info(f"BM25 检索完成，返回 {len(results)} 条结果")
        return results

    def rrf_fuse(
        self,
        vector_results: List[Dict],
        bm25_results: List[Dict],
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        RRF（Reciprocal Rank Fusion）融合

        将向量检索和 BM25 检索的结果按排名融合
        公式: score(d) = 1/(k + rank_v(d)) + 1/(k + rank_b(d))

        参数:
            vector_results: 向量检索结果列表
            bm25_results: BM25 检索结果列表
            k: RRF 融合常数（默认60）

        返回:
            融合后的排序结果列表
        """
        fused_scores = {}     # 文档内容 -> 融合分数
        content_map = {}      # 文档内容 -> 元数据

        # 处理向量检索结果
        for result in vector_results:
            content = result["content"]
            rank = result["rank"]
            rrf_score = 1.0 / (k + rank)
            fused_scores[content] = fused_scores.get(content, 0) + rrf_score

            if content not in content_map:
                content_map[content] = {
                    "content": content,
                    "law": result.get("law", ""),
                    "article": result.get("article", ""),
                    "title": result.get("title", ""),
                    "category": result.get("category", ""),
                    "source": result.get("source", ""),
                    "doc_id": result.get("doc_id", 0)
                }

        # 处理 BM25 检索结果
        for result in bm25_results:
            content = result["content"]
            rank = result["rank"]
            rrf_score = 1.0 / (k + rank)
            fused_scores[content] = fused_scores.get(content, 0) + rrf_score

            if content not in content_map:
                content_map[content] = {
                    "content": content,
                    "law": result.get("law", ""),
                    "article": result.get("article", ""),
                    "title": result.get("title", ""),
                    "category": result.get("category", ""),
                    "source": result.get("source", ""),
                    "doc_id": result.get("doc_id", 0)
                }

        # 按融合分数降序排序
        sorted_contents = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)

        # 构建最终结果
        fused_results = []
        for content, score in sorted_contents:
            result = content_map[content].copy()
            result["rrf_score"] = score
            result["rank"] = len(fused_results) + 1
            fused_results.append(result)

        logger.info(f"RRF 融合完成，融合后 {len(fused_results)} 条结果")
        return fused_results

    def retrieve(self, query: str, top_k: int = 20) -> List[Dict[str, Any]]:
        """
        混合检索主入口

        流程: 向量检索 Top-K + BM25 Top-K → RRF 融合

        参数:
            query: 查询文本
            top_k: 每路检索返回数量

        返回:
            融合后的检索结果列表
        """
        # 向量检索
        vector_results = self.vector_search(query, top_k=settings.VECTOR_TOP_K)

        # BM25 检索
        bm25_results = self.bm25_search(query, top_k=settings.BM25_TOP_K)

        # RRF 融合
        fused_results = self.rrf_fuse(
            vector_results,
            bm25_results,
            k=settings.RRF_K
        )

        logger.info(
            f"混合检索完成: 向量 {len(vector_results)} 条, "
            f"BM25 {len(bm25_results)} 条, "
            f"融合 {len(fused_results)} 条"
        )

        return fused_results

    def insert_documents(self, chunks: List[str], embeddings: np.ndarray, doc_id: int):
        """
        向 Milvus 插入文档向量

        参数:
            chunks: 文本块列表
            embeddings: 对应的向量数组
            doc_id: 所属文档ID
        """
        if self.collection is None:
            logger.warning("Milvus 未连接，跳过向量插入")
            return

        data = [
            embeddings.tolist(),              # 向量
            chunks,                           # 文本内容
            [doc_id] * len(chunks),           # 文档ID
            [f"doc_{doc_id}"] * len(chunks)   # 来源标识
        ]
        self.collection.insert(data)
        self.collection.flush()
        logger.info(f"向 Milvus 插入 {len(chunks)} 条向量（文档ID: {doc_id}）")


# 全局单例
_retriever = None


def get_retriever() -> HybridRetriever:
    """获取全局 HybridRetriever 单例实例"""
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever
