"""
劳动合同纠纷智能问答系统 - 合同研判引擎

对劳动合同文本进行逐条法律风险分析，流程：
1. 使用 LLM（DeepSeek API）将合同全文拆分为独立条款
2. 对每条条款进行 RAG 检索（术语扩展→混合检索→重排序）
3. 对每条条款使用 LLM 进行法律风险分析
4. 汇总所有条款的分析结果，生成总体评估

输出：
- 条款总数
- 风险等级统计（高/中/低）
- 逐条分析结果（条款原文、风险等级、风险描述、法律依据、修改建议）
- 总体评估
"""
import logging
from typing import List, Dict, Any
from config import settings

logger = logging.getLogger(__name__)


class ContractAnalyzer:
    """
    合同研判引擎

    将合同拆分为条款后逐条分析，结合 RAG 检索的法律依据，
    使用 DeepSeek API 生成专业风险评估报告
    """

    def __init__(self):
        """初始化研判引擎（延迟加载组件）"""
        self._generator = None
        self._retriever = None
        self._reranker = None
        self._expander = None

    # ========== 延迟加载各组件（使用全局单例）==========

    @property
    def generator(self):
        """回答生成器（延迟加载）"""
        if self._generator is None:
            from rag.generator import get_generator
            self._generator = get_generator()
        return self._generator

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
    def expander(self):
        """同义词扩展器（延迟加载）"""
        if self._expander is None:
            from rag.synonym_expander import get_expander
            self._expander = get_expander()
        return self._expander

    def analyze(self, contract_text: str) -> Dict[str, Any]:
        """
        分析合同文本，生成研判报告

        参数:
            contract_text: 劳动合同全文文本

        返回:
            包含以下字段的字典:
            - total_clauses: 条款总数
            - risk_summary: 风险等级统计 {高: N, 中: N, 低: N}
            - clauses: 逐条分析结果列表
            - overall_assessment: 总体评估文本
        """
        logger.info("合同研判启动")
        logger.info(f"合同文本长度: {len(contract_text)} 字符")

        # ========== Step 1: 使用 LLM 拆分条款 ==========
        clauses = self.generator.split_clauses(contract_text)
        logger.info(f"[Step 1] 合同拆分完成，共 {len(clauses)} 条条款")

        # ========== Step 2: 逐条分析 ==========
        clause_analyses = []
        for i, clause in enumerate(clauses):
            logger.info(f"[Step 2] 正在分析第 {i + 1}/{len(clauses)} 条条款")

            # 2.1 术语扩展
            expanded_clause = self.expander.expand(clause)

            # 2.2 RAG 检索相关法条
            retrieved_docs = self.retriever.retrieve(expanded_clause)

            # 2.3 重排序
            reranked_docs = self.reranker.rerank(
                clause,
                retrieved_docs,
                top_k=settings.RERANK_TOP_K
            )

            # 2.4 LLM 分析法律风险
            analysis = self.generator.generate_analysis(clause, reranked_docs)

            # 构建条款分析结果
            clause_analysis = {
                "clause_index": i + 1,
                "clause_text": clause,
                "risk_level": analysis.get("risk_level", "未知"),
                "risk_description": analysis.get("risk_description", ""),
                "legal_basis": analysis.get("legal_basis", []),
                "suggestion": analysis.get("suggestion", "")
            }
            clause_analyses.append(clause_analysis)

        # ========== Step 3: 汇总报告 ==========
        risk_summary = self._summarize_risks(clause_analyses)
        overall_assessment = self._generate_overall_assessment(
            clause_analyses, risk_summary
        )

        result = {
            "total_clauses": len(clauses),
            "risk_summary": risk_summary,
            "clauses": clause_analyses,
            "overall_assessment": overall_assessment
        }

        logger.info("合同研判完成")
        return result

    def _summarize_risks(self, clause_analyses: List[Dict]) -> Dict[str, int]:
        """
        统计各风险等级的条款数量

        参数:
            clause_analyses: 条款分析结果列表

        返回:
            风险等级统计字典 {高: N, 中: N, 低: N}
        """
        summary = {"高": 0, "中": 0, "低": 0}
        for analysis in clause_analyses:
            level = analysis.get("risk_level", "未知")
            if level in summary:
                summary[level] += 1
            else:
                # 未知风险等级归为低风险
                summary["低"] += 1
        return summary

    def _generate_overall_assessment(
        self,
        clause_analyses: List[Dict],
        risk_summary: Dict[str, int]
    ) -> str:
        """
        根据逐条分析结果生成总体评估

        参数:
            clause_analyses: 条款分析结果列表
            risk_summary: 风险等级统计

        返回:
            总体评估文本
        """
        total = len(clause_analyses)
        high = risk_summary.get("高", 0)
        medium = risk_summary.get("中", 0)
        low = risk_summary.get("低", 0)

        if high > 0:
            assessment = (
                f"本次研判共分析 {total} 条条款，"
                f"其中高风险 {high} 条、中风险 {medium} 条、低风险 {low} 条。"
                f"合同存在较严重的法律风险，建议重点关注高风险条款，"
                f"及时修改或删除违法条款，并寻求专业律师意见。"
            )
        elif medium > 0:
            assessment = (
                f"本次研判共分析 {total} 条条款，"
                f"其中中风险 {medium} 条、低风险 {low} 条。"
                f"合同存在一定法律风险，建议对中风险条款进行修改完善，"
                f"补充必要的保护性条款，防范潜在法律纠纷。"
            )
        else:
            assessment = (
                f"本次研判共分析 {total} 条条款，"
                f"全部为低风险。"
                f"合同整体合规性较好，未发现明显法律风险。"
                f"建议定期复查，确保持续符合法律法规要求。"
            )

        return assessment


# 全局单例
_analyzer = None


def get_analyzer() -> ContractAnalyzer:
    """获取全局 ContractAnalyzer 单例实例"""
    global _analyzer
    if _analyzer is None:
        _analyzer = ContractAnalyzer()
    return _analyzer
