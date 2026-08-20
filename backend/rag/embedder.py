"""
劳动合同纠纷智能问答系统 - 向量编码器

使用 BGE 中文向量模型（BAAI/bge-small-zh-v1.1）将文本编码为向量，
支持加载 LoRA 微调权重以提升在劳动法领域的编码效果。

功能：
1. 批量文本编码（用于知识库文档入库）
2. 单条查询编码（用于检索时的查询向量化）
3. LoRA 微调模型加载（可选）
"""
import logging
from typing import List
import numpy as np
from config import settings

logger = logging.getLogger(__name__)


class Embedder:
    """
    BGE 向量模型封装

    默认使用 BAAI/bge-small-zh-v1.1（512维），支持通过 LoRA 进行领域微调
    """

    def __init__(self):
        """初始化向量模型"""
        from sentence_transformers import SentenceTransformer

        logger.info(f"正在加载向量模型: {settings.EMBEDDING_MODEL}")
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)

        # 如果配置了 LoRA 微调权重路径，则加载
        if settings.LORA_MODEL_PATH:
            self._load_lora_weights()

        # 获取向量维度
        self.dimension = self.model.get_sentence_embedding_dimension()
        logger.info(f"向量模型加载完成，向量维度: {self.dimension}")

    def _load_lora_weights(self):
        """
        加载 LoRA 微调权重到基础模型上

        使用 PEFT 库将 LoRA adapter 加载到 SentenceTransformer 的底层 transformer 模型上，
        以提升在劳动法领域的文本编码效果
        """
        try:
            from peft import PeftModel

            # 获取 SentenceTransformer 内部的 transformer 模型
            base_model = self.model._first_module().auto_model

            # 加载 LoRA adapter
            self.model._first_module().auto_model = PeftModel.from_pretrained(
                base_model,
                settings.LORA_MODEL_PATH
            )
            logger.info(f"LoRA 微调权重加载成功: {settings.LORA_MODEL_PATH}")
        except Exception as e:
            logger.warning(f"LoRA 权重加载失败，将使用基础模型: {e}")

    def encode(self, texts: List[str]) -> np.ndarray:
        """
        批量编码文本为向量

        参数:
            texts: 文本列表

        返回:
            numpy 数组，形状为 (len(texts), dimension)，已 L2 归一化
        """
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,   # L2 归一化，便于内积检索
            show_progress_bar=False
        )
        return np.array(embeddings)

    def encode_query(self, text: str) -> np.ndarray:
        """
        编码单条查询文本为向量

        参数:
            text: 查询文本

        返回:
            numpy 数组，形状为 (dimension,)，已 L2 归一化
        """
        embedding = self.model.encode(
            [text],
            normalize_embeddings=True,
            show_progress_bar=False
        )
        return np.array(embedding[0])


# 全局单例（避免重复加载模型）
_embedder = None


def get_embedder() -> Embedder:
    """获取全局 Embedder 单例实例"""
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder
