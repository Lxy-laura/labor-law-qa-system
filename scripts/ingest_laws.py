#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
法律文档导入脚本

功能说明：
    1. 解析法律文本文件（JSON格式法条数据）
    2. 按法条粒度进行分块
    3. 使用 BAAI/bge-large-zh-v1.5 模型对每个法条进行向量化
    4. 将向量数据存入 Milvus 向量数据库

使用方法：
    python scripts/ingest_laws.py

环境变量（可在 .env 中配置）：
    MILVUS_HOST=127.0.0.1
    MILVUS_PORT=19530
    MILVUS_COLLECTION=legal_articles
    EMBEDDING_MODEL=BAAI/bge-large-zh-v1.5
"""

import json
import os
import time
from pathlib import Path
from typing import List, Dict

# ============================================================
# 配置区
# ============================================================

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 法条数据文件
LAWS_DATA_FILE = PROJECT_ROOT / "data" / "sample_laws.json"

# 嵌入模型名称
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "BAAI/bge-large-zh-v1.5")

# Milvus 配置
MILVUS_HOST = os.environ.get("MILVUS_HOST", "127.0.0.1")
MILVUS_PORT = os.environ.get("MILVUS_PORT", "19530")
MILVUS_COLLECTION = os.environ.get("MILVUS_COLLECTION", "legal_articles")

# 向量维度（bge-large-zh-v1.5 输出维度为1024）
VECTOR_DIMENSION = 1024


def load_law_data() -> List[Dict]:
    """
    加载法律文本数据

    返回:
        法条列表，每条包含 law_name, article_number, content, keywords 等
    """
    with open(LAWS_DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    laws = data.get("laws", [])
    print(f"[信息] 加载法条数据: {len(laws)} 条")
    return laws


def chunk_law_articles(laws: List[Dict]) -> List[Dict]:
    """
    按法条粒度对法律文本进行分块

    参数:
        laws: 原始法条数据列表

    返回:
        分块后的数据列表，每个分块包含完整文本用于向量化
    """
    chunks = []
    for i, law in enumerate(laws):
        law_name = law["law_name"]
        law_short = law.get("law_short_name", law_name)
        article_number = law["article_number"]
        title = law.get("title", "")
        content = law["content"]
        keywords = law.get("keywords", [])
        category = law.get("category", "")

        # 构建用于向量化的完整文本（拼接法条编号+标题+正文）
        full_text = f"{law_short} {article_number} {title}\n{content}"

        # 同时构建一个搜索文本（包含关键词以增强检索效果）
        search_text = f"{law_short} {article_number} {title} {' '.join(keywords)}\n{content}"

        chunks.append(
            {
                "id": i,
                "law_name": law_name,
                "law_short_name": law_short,
                "article_number": article_number,
                "article_no": law.get("article_no", 0),
                "title": title,
                "content": content,
                "keywords": keywords,
                "category": category,
                "vector_text": search_text,  # 用于向量化的文本
                "full_text": full_text,
            }
        )

    print(f"[信息] 法条分块完成: {len(chunks)} 个分块")
    return chunks


def load_embedding_model():
    """
    加载 BGE 嵌入模型

    返回:
        SentenceTransformer 模型实例
    """
    from sentence_transformers import SentenceTransformer

    print(f"[信息] 正在加载嵌入模型: {EMBEDDING_MODEL}")
    print("[信息] 首次运行会从HuggingFace下载模型，请耐心等待...")

    model = SentenceTransformer(EMBEDDING_MODEL)
    model.max_seq_length = 512  # 法条文本较长，设置足够的序列长度

    # 获取模型输出维度
    test_embedding = model.encode(["测试"])
    dim = test_embedding.shape[1]
    print(f"[信息] 模型加载完成，向量维度: {dim}")

    return model


def create_milvus_collection():
    """
    创建 Milvus 向量集合

    返回:
        Milvus 连接对象
    """
    from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

    # 连接到 Milvus
    print(f"[信息] 连接 Milvus: {MILVUS_HOST}:{MILVUS_PORT}")
    connections.connect(
        alias="default",
        host=MILVUS_HOST,
        port=MILVUS_PORT,
    )

    # 如果集合已存在则删除重建
    if utility.has_collection(MILVUS_COLLECTION):
        print(f"[信息] 集合 '{MILVUS_COLLECTION}' 已存在，删除并重建")
        utility.drop_collection(MILVUS_COLLECTION)

    # 定义集合字段
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=False),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=VECTOR_DIMENSION),
        FieldSchema(name="law_name", dtype=DataType.VARCHAR, max_length=256),
        FieldSchema(name="article_number", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=256),
        FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=4096),
        FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=64),
    ]

    schema = CollectionSchema(
        fields=fields,
        description="劳动法律条文向量集合",
        enable_dynamic_field=True,
    )

    collection = Collection(
        name=MILVUS_COLLECTION,
        schema=schema,
        using="default",
    )

    # 创建索引（IVF_FLAT 索引，适合中小规模数据）
    index_params = {
        "index_type": "IVF_FLAT",
        "metric_type": "IP",  # 内积（Inner Product），配合归一化向量即为余弦相似度
        "params": {"nlist": 128},
    }
    collection.create_index(field_name="vector", index_params=index_params)
    print(f"[信息] 集合 '{MILVUS_COLLECTION}' 创建完成，索引类型: IVF_FLAT")

    # 加载集合到内存
    collection.load()
    print(f"[信息] 集合已加载到内存")

    return collection


def vectorize_and_store(model, chunks: List[Dict]):
    """
    对法条文本进行向量化并存入 Milvus

    参数:
        model: SentenceTransformer 嵌入模型
        chunks: 法条分块数据列表
    """
    # 创建 Milvus 集合
    collection = create_milvus_collection()

    # 提取向量化所需的文本
    texts = [chunk["vector_text"] for chunk in chunks]

    # 批量向量化
    print(f"\n[信息] 开始向量化 {len(texts)} 条法条文本...")
    t0 = time.time()
    # 归一化向量（配合IP度量即为余弦相似度）
    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True,
    )
    print(f"[信息] 向量化完成，耗时: {time.time() - t0:.2f}s")
    print(f"[信息] 向量矩阵形状: {embeddings.shape}")

    # 准备插入数据
    ids = [chunk["id"] for chunk in chunks]
    vectors = embeddings.tolist()
    law_names = [chunk["law_name"] for chunk in chunks]
    article_numbers = [chunk["article_number"] for chunk in chunks]
    titles = [chunk["title"] for chunk in chunks]
    contents = [chunk["content"][:4000] for chunk in chunks]  # 截断超长文本
    categories = [chunk["category"] for chunk in chunks]

    # 插入数据到 Milvus
    print(f"\n[信息] 向 Milvus 插入向量数据...")
    collection.insert(
        [
            ids,
            vectors,
            law_names,
            article_numbers,
            titles,
            contents,
            categories,
        ]
    )
    # 确保数据写入磁盘
    collection.flush()

    print(f"[完成] 成功插入 {len(ids)} 条向量数据到 Milvus")
    print(f"  - 集合名称: {MILVUS_COLLECTION}")
    print(f"  - 向量维度: {VECTOR_DIMENSION}")
    print(f"  - 索引类型: IVF_FLAT (IP度量)")

    # 断开连接
    from pymilvus import connections
    connections.disconnect("default")


def verify_ingestion():
    """验证向量化结果：进行一次测试检索"""
    from pymilvus import connections, Collection

    connections.connect(alias="default", host=MILVUS_HOST, port=MILVUS_PORT)
    collection = Collection(MILVUS_COLLECTION)
    collection.load()

    # 查询集合中的数据量
    count = collection.num_entities
    print(f"\n[验证] 集合 '{MILVUS_COLLECTION}' 中共 {count} 条记录")

    # 测试检索
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(EMBEDDING_MODEL)

    # 用一个自然语言问题进行检索测试
    test_query = "公司不签劳动合同要赔偿双倍工资吗"
    print(f"[验证] 测试检索: '{test_query}'")

    query_vector = model.encode([test_query], normalize_embeddings=True).tolist()

    results = collection.search(
        data=query_vector,
        anns_field="vector",
        param={"metric_type": "IP", "params": {"nprobe": 10}},
        limit=3,
        output_fields=["law_name", "article_number", "title", "content"],
    )

    print(f"[验证] 检索结果 Top 3:")
    for i, hit in enumerate(results[0]):
        entity = hit.entity
        print(f"  {i+1}. [{hit.score:.4f}] {entity.get('law_name', '')} {entity.get('article_number', '')} - {entity.get('title', '')}")

    connections.disconnect("default")


def main():
    """主函数：法律文档导入的完整流程"""
    print("=" * 60)
    print("法律文档向量化导入")
    print("=" * 60)

    # 第一步：加载法条数据
    laws = load_law_data()
    if not laws:
        print("[错误] 法条数据为空")
        return

    # 第二步：按法条分块
    chunks = chunk_law_articles(laws)

    # 第三步：加载嵌入模型
    model = load_embedding_model()

    # 第四步：向量化并存入 Milvus
    vectorize_and_store(model, chunks)

    # 第五步：验证导入结果
    print("\n" + "-" * 60)
    print("[信息] 开始验证导入结果...")
    verify_ingestion()

    print("\n" + "=" * 60)
    print("法律文档向量化导入完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
