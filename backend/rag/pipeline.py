"""
劳动合同纠纷智能问答系统 - RAG 管线编排

数据来源（唯一来源）：
- 知识库文档：SQLite documents 表（管理员通过知识库管理页面上传的文档）

没有任何预置的 JSON 数据文件。同义词扩展、案例推荐、落地服务全部由
DeepSeek API 根据上传的文档内容和用户问题实时生成。

问答流程：
Step 1: BM25 检索（只搜管理员上传到知识库的文档）
Step 2: 调用 DeepSeek API（把检索到的文档内容 + 用户问题发给 AI）
        AI 一次性生成：法律回答 + 相似案例 + 维权热线和行动指南
Step 3: 置信度计算
Step 4: 构建引用

注意：如果管理员没有上传任何文档，系统会提示"知识库为空，请先上传文档"。
"""
import math
import logging
from typing import List, Dict, Any
from config import settings

logger = logging.getLogger(__name__)


class RAGPipeline:
    """RAG 管线编排器"""

    def __init__(self):
        self._articles = []         # 知识库文档列表（从数据库加载，已分块）
        self._bm25_index = None    # BM25 索引
        self._load_data()

    def _load_data(self):
        """
        加载所有数据

        唯一数据来源：管理员通过知识库管理页面上传的文档（SQLite documents 表）
        不再加载任何预置的 JSON 文件
        """

        # ========== 1. 从数据库加载知识库文档 ==========
        # 管理员在知识库管理页面上传的文档，indexed=1 的才会被加载
        # 每个文档的全文会被切成 500 字一块，加入 BM25 索引
        try:
            from database import get_connection
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT id, title, content, doc_type FROM documents WHERE indexed = 1")
            rows = cur.fetchall()
            cur.close()
            conn.close()

            db_chunk_count = 0
            for row in rows:
                content = row["content"] or ""
                title = row["title"]
                doc_type = row["doc_type"] or "法律法规"

                # 把上传文档的全文切成块，用于 BM25 检索
                chunks = self._chunk_text(content, chunk_size=500, overlap=50)
                for i, chunk in enumerate(chunks):
                    self._articles.append({
                        "content": chunk,
                        "law": title,              # 法律名称 = 文档标题
                        "article": f"第{i+1}段",    # 条款编号 = 第N段
                        "title": title,
                        "category": doc_type
                    })
                    db_chunk_count += 1

            if db_chunk_count > 0:
                logger.info(f"知识库文档加载成功：{len(rows)} 个文档，共 {db_chunk_count} 个文本块")
            else:
                logger.warning("知识库为空！管理员尚未上传任何文档，问答功能将无法正常工作")
        except Exception as e:
            logger.warning(f"知识库文档加载失败: {e}")

        # ========== 2. 构建 BM25 索引 ==========
        # 用所有上传的文档块构建 BM25 索引
        # BM25 是一种关键词匹配算法，根据词频和文档长度计算相关度分数
        try:
            if self._articles:
                from rank_bm25 import BM25Okapi
                # list() 把每个中文字符当作一个 token（中文不需要分词器）
                tokenized_docs = [list(art["content"]) for art in self._articles]
                self._bm25_index = BM25Okapi(tokenized_docs)
                logger.info(f"BM25 索引构建完成，共 {len(self._articles)} 个文本块")
        except Exception as e:
            logger.warning(f"BM25 索引构建失败: {e}")
            self._bm25_index = None

    def reload(self):
        """
        重新加载所有数据

        当管理员上传/删除文档后，kb.py 会调用这个方法，
        让变更立即生效，用户下一次提问就会搜索到新上传的文档
        """
        logger.info("开始重新加载 RAG 管线数据...")
        self._articles = []
        self._bm25_index = None
        self._load_data()
        logger.info("RAG 管线数据重新加载完成")

    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> list:
        """
        将长文本切分为重叠的块

        参数:
            chunk_size: 每块最大字符数（500字）
            overlap: 相邻块之间的重叠字符数（50字，防止句子被截断）

        例如一篇 1200 字的文档会被切成 3 块：
            第1块：0-500字
            第2块：450-950字（与第1块重叠50字）
            第3块：900-1200字（与第2块重叠50字）
        """
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = end - overlap
        return chunks

    def _bm25_search(self, query: str, top_k: int = 10) -> List[Dict]:
        """
        BM25 关键词检索

        在管理员上传的知识库文档中搜索最相关的内容
        BM25 算法根据词频（关键词出现次数）和文档长度计算相关度分数
        返回得分最高的 top_k 条结果
        """
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
        """
        生成回答

        调用 DeepSeek API，把检索到的文档内容 + 用户问题发给 AI
        AI 一次性生成完整的法律回答，包含：
        1. 法律条文解读
        2. 相似案例推荐
        3. 维权热线和行动指南

        如果知识库为空（没有上传任何文档），返回提示信息
        如果没有配置 API Key，返回检索到的文档内容拼接
        """
        # 知识库为空时的提示
        if not contexts:
            return ("当前知识库为空，无法回答您的问题。\n\n"
                    "请管理员先在「知识库管理」页面上传劳动合同相关法律文档（如《劳动合同法》.docx），"
                    "上传后系统即可自动检索并回答问题。")

        # 拼接检索到的文档内容作为上下文
        context_text = "\n\n".join([
            f"[{i+1}] {ctx['law']} {ctx['article']}\n{ctx['content']}"
            for i, ctx in enumerate(contexts)
        ])

        # 尝试使用 DeepSeek API 生成回答
        if settings.DEEPSEEK_API_KEY and settings.DEEPSEEK_API_KEY != "your_api_key_here":
            try:
                from openai import OpenAI
                client = OpenAI(
                    api_key=settings.DEEPSEEK_API_KEY,
                    base_url=settings.DEEPSEEK_BASE_URL
                )

                # 系统提示词：要求 AI 同时生成法律回答、案例推荐、维权热线
                system_prompt = (
                    "你是一位专业的劳动合同法律顾问，精通《劳动合同法》及相关劳动法规。"
                    "请基于提供的法律文档内容，准确、专业地回答用户的劳动合同纠纷问题。"
                    "你的回答必须包含以下三个部分：\n"
                    "一、法律分析与建议：引用相关法律条文，用通俗语言解释，给出实用建议\n"
                    "二、相似案例参考：根据问题类型，推荐1-2个类似的劳动争议典型案例（包括案件名称、案情简介、判决要点）\n"
                    "三、维权途径：推荐相关的维权热线（如12333人社热线、12348法援热线等）和具体行动步骤"
                )

                user_prompt = f"""请根据以下法律文档内容，回答用户的劳动合同纠纷问题。

【相关法律文档参考】
{context_text}

【用户问题】
{query}

请按照以下格式回答：

## 法律分析与建议
（引用相关法律条文，用通俗易懂的语言解释法律含义，给出具体的维权建议）

## 相似案例参考
（推荐1-2个类似的劳动争议典型案例，包括案件名称、案情简介、判决要点）

## 维权途径
（推荐相关维权热线和具体行动步骤，如拨打12333、12348，向劳动监察大队投诉等）"""

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

        # 无 API Key 时，返回文档匹配结果
        answer_parts = [f"根据您的提问「{query}」，为您检索到以下相关法律文档内容：\n"]
        for i, ctx in enumerate(contexts[:5], 1):
            answer_parts.append(
                f"{i}. 《{ctx['law']}》{ctx['article']}（{ctx.get('title', '')}）\n"
                f"   {ctx['content']}\n"
            )
        answer_parts.append("\n⚠️ 提示：当前未配置 DeepSeek API Key，以上为文档匹配结果。"
                           "配置 API Key 后可获得 AI 智能解读。")
        return "\n".join(answer_parts)

    def run_debug(self, query: str, top_k: int = 10) -> Dict[str, Any]:
        """
        调试用：执行 RAG 管线并返回每一步的中间结果

        用于「检索调试」页面，展示：
        1. 查询处理（分词）
        2. BM25 检索（召回的文档和分数）
        3. 上下文构建（归一化排序、选 Top-K）
        4. 生成回答（LLM 输出）
        """
        import time

        debug_data = {
            "query": query,
            "pipeline_info": {
                "total_chunks": len(self._articles),
                "algorithm": "BM25 (rank_bm25)",
                "chunk_size": 500,
                "overlap": 50,
                "has_api_key": bool(settings.DEEPSEEK_API_KEY and settings.DEEPSEEK_API_KEY != "your_api_key_here"),
                "model": settings.DEEPSEEK_MODEL
            },
            "step1_query": None,
            "step2_retrieval": None,
            "step3_context": None,
            "step4_generation": None,
            "retrieved_docs": None
        }

        # ===== Step 1: 查询处理 =====
        t0 = time.time()
        tokenized_query = list(query)
        debug_data["step1_query"] = {
            "query": query,
            "tokens": tokenized_query[:20],
            "token_count": len(tokenized_query),
            "time_ms": round((time.time() - t0) * 1000, 1)
        }
        logger.info(f"[Debug] Step 1 查询处理完成，{len(tokenized_query)} 个 token")

        # ===== Step 2: BM25 检索 =====
        t0 = time.time()
        retrieved_docs = self._bm25_search(query, top_k=20)
        debug_data["step2_retrieval"] = {
            "algorithm": "BM25 (rank_bm25)",
            "candidates": len(retrieved_docs),
            "time_ms": round((time.time() - t0) * 1000, 1)
        }
        logger.info(f"[Debug] Step 2 BM25 检索完成，{len(retrieved_docs)} 条结果")

        # ===== Step 3: 上下文构建（归一化分数，选 Top-K） =====
        t0 = time.time()
        if retrieved_docs:
            max_score = max(doc.get("score", 0) for doc in retrieved_docs)
            if max_score <= 0:
                max_score = 1.0
            top_docs = retrieved_docs[:top_k]
            ranked = []
            for doc in top_docs:
                normalized_score = doc.get("score", 0) / max_score
                ranked.append({
                    "title": doc.get("title", ""),
                    "law": doc.get("law", ""),
                    "article": doc.get("article", ""),
                    "score": round(normalized_score, 4),
                    "raw_score": round(doc.get("score", 0), 4),
                    "snippet": doc.get("content", "")[:150] + "..." if len(doc.get("content", "")) > 150 else doc.get("content", ""),
                    "content": doc.get("content", ""),
                    "category": doc.get("category", "")
                })
        else:
            ranked = []

        debug_data["step3_context"] = {
            "topK": len(ranked),
            "ranked": ranked,
            "time_ms": round((time.time() - t0) * 1000, 1)
        }
        debug_data["retrieved_docs"] = ranked
        logger.info(f"[Debug] Step 3 上下文构建完成，{len(ranked)} 条 Top-K 结果")

        # ===== Step 4: 生成回答 =====
        t0 = time.time()
        answer = self._generate_answer(query, retrieved_docs[:top_k] if retrieved_docs else [])
        gen_time = round((time.time() - t0) * 1000, 1)
        debug_data["step4_generation"] = {
            "answer": answer,
            "time_ms": gen_time,
            "tokens": len(answer),
            "model": settings.DEEPSEEK_MODEL if settings.DEEPSEEK_API_KEY and settings.DEEPSEEK_API_KEY != "your_api_key_here" else "无 API Key（返回文档匹配结果）"
        }
        logger.info(f"[Debug] Step 4 回答生成完成，{len(answer)} 字符")

        return debug_data

    def run(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        执行完整 RAG 管线 — 用户提问后调用这个方法

        完整流程：
        1. BM25 检索：在管理员上传的文档中搜索最相关的内容
        2. 生成回答：把检索到的内容 + 问题发给 DeepSeek，AI 一次性生成
           法律回答 + 相似案例 + 维权热线
        3. 置信度计算：基于 BM25 分数算一个百分比
        4. 构建引用：把检索到的文档作为引用来源返回
        """
        logger.info(f"RAG 管线启动，用户问题: {query}")

        # Step 1: BM25 检索（只搜管理员上传到知识库的文档）
        retrieved_docs = self._bm25_search(query, top_k=20)
        logger.info(f"[Step 1] BM25 检索完成，获取 {len(retrieved_docs)} 条结果")

        # Step 2: 生成回答（法律回答 + 相似案例 + 维权热线全部由 DeepSeek 生成）
        answer = self._generate_answer(query, retrieved_docs)
        logger.info("[Step 2] 回答生成完成")

        # Step 3: 置信度计算
        # 基于 BM25 最高分用 log1p 压缩后映射到 0.55-0.95 区间
        # 检索结果多就加点分，最多加 0.03
        if retrieved_docs:
            max_score = max(doc.get("score", 0) for doc in retrieved_docs)
            normalized = math.log1p(max_score) / math.log1p(50)
            confidence = 0.55 + normalized * 0.37
            hit_bonus = min(len(retrieved_docs) / 20 * 0.03, 0.03)
            confidence = min(confidence + hit_bonus, 0.95)
        else:
            confidence = 0.3

        # Step 4: 构建引用
        # 将 BM25 分数归一化到 0-1 范围，作为"相关度"显示在前端
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

        result = {
            "answer": answer,
            "citations": citations,
            "cases": [],              # 案例由 DeepSeek 在回答中生成，不再单独返回
            "landing_services": [],   # 维权热线由 DeepSeek 在回答中生成，不再单独返回
            "confidence": round(confidence, 4),
            "expanded_query": query   # 不再做同义词扩展，直接用原始问题
        }

        logger.info("RAG 管线执行完成")
        return result


# 全局单例
_pipeline = None


def get_pipeline() -> RAGPipeline:
    """获取 RAG 管线全局单例"""
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline()
    return _pipeline
