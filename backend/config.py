"""
劳动合同纠纷智能问答系统 - 配置文件

从环境变量读取所有敏感配置（DeepSeek API Key、JWT 密钥等），
提供合理的默认值，确保系统在没有配置时也能启动（功能受限）。
"""
import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
# 明确从 backend 目录加载 .env，确保无论从哪个目录启动都能找到
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(_env_path)
# 同时也加载工作目录下的 .env（如果存在，不覆盖已加载的值）
load_dotenv(override=False)

class Config:
    """系统全局配置类，所有配置通过环境变量读取"""

    # ========== DeepSeek API 配置 ==========
    # DeepSeek API 密钥（必填，用于调用 LLM 生成回答）
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    # DeepSeek API 基础 URL
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    # 使用的模型名称
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    # 最大生成 Token 数
    DEEPSEEK_MAX_TOKENS = int(os.getenv("DEEPSEEK_MAX_TOKENS", "2048"))
    # 生成温度（越低越确定性）
    DEEPSEEK_TEMPERATURE = float(os.getenv("DEEPSEEK_TEMPERATURE", "0.3"))

    # ========== Milvus 向量数据库配置（可选，未安装时自动降级为 BM25 检索）==========
    MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
    MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
    MILVUS_COLLECTION = os.getenv("MILVUS_COLLECTION", "labor_law_docs")
    # 向量维度（BAAI/bge-small-zh-v1.1 为 512 维）
    MILVUS_DIMENSION = int(os.getenv("MILVUS_DIMENSION", "512"))

    # ========== JWT 认证配置 ==========
    JWT_SECRET = os.getenv("JWT_SECRET", "labor-law-qa-secret-key-2024")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

    # ========== 模型路径配置 ==========
    # BGE 中文向量模型（用于文本向量化）
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.1")
    # BGE Cross-Encoder 重排序模型
    RERANKER_MODEL = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-base")
    # LoRA 微调模型路径（为空则使用基础模型）
    LORA_MODEL_PATH = os.getenv("LORA_MODEL_PATH", "")

    # ========== 应用配置 ==========
    APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT = int(os.getenv("APP_PORT", "8000"))
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"

    # ========== 数据文件路径 ==========
    DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    SYNONYM_DICT_PATH = os.path.join(DATA_DIR, "synonym_dict.json")
    LEGAL_ARTICLES_PATH = os.path.join(DATA_DIR, "legal_articles.json")

    # ========== 检索参数配置 ==========
    VECTOR_TOP_K = int(os.getenv("VECTOR_TOP_K", "20"))
    BM25_TOP_K = int(os.getenv("BM25_TOP_K", "20"))
    RERANK_TOP_K = int(os.getenv("RERANK_TOP_K", "5"))
    # RRF 融合常数（通常为 60）
    RRF_K = int(os.getenv("RRF_K", "60"))

# 全局配置实例
settings = Config()