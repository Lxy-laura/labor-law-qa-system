"""
劳动合同纠纷智能问答系统 - 回答生成器

使用 DeepSeek API（通过 openai SDK 调用）生成回答。
base_url 设为 https://api.deepseek.com/v1，使用 deepseek-chat 模型。

功能：
1. generate() - 根据问题和检索到的法条上下文生成回答
2. generate_analysis() - 针对单条合同条款生成法律风险分析（JSON 格式）
3. split_clauses() - 使用 LLM 将合同全文拆分为独立条款
"""
import json
import logging
from typing import List, Dict, Any, Optional
from config import settings

logger = logging.getLogger(__name__)


class Generator:
    """
    回答生成器

    使用 DeepSeek API 生成回答，通过 openai SDK 调用，
    base_url 设为 https://api.deepseek.com/v1
    """

    def __init__(self):
        """初始化 DeepSeek 客户端"""
        from openai import OpenAI

        # 使用 openai SDK，base_url 指向 DeepSeek API
        self.client = OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL
        )
        self.model = settings.DEEPSEEK_MODEL
        logger.info(f"DeepSeek 客户端初始化完成，模型: {self.model}")

    def generate(
        self,
        query: str,
        contexts: List[Dict[str, Any]],
        system_prompt: Optional[str] = None
    ) -> str:
        """
        根据用户问题和检索到的法条上下文生成回答

        参数:
            query: 用户问题
            contexts: 检索到的法条上下文列表
            system_prompt: 自定义系统提示词（可选）

        返回:
            生成的回答文本
        """
        # 构建法条上下文文本
        context_text = self._build_context(contexts)

        # 系统提示词
        if system_prompt is None:
            system_prompt = self._default_system_prompt()

        # 用户提示
        user_prompt = f"""请根据以下法律法规内容，回答用户的劳动合同纠纷问题。

【相关法条参考】
{context_text}

【用户问题】
{query}

请按以下要求回答：
1. 准确引用相关法条（标明法律名称和条款编号）
2. 用通俗易懂的语言解释法律含义
3. 给出具体的维权建议
4. 如果法条中没有直接相关内容，请如实说明"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=settings.DEEPSEEK_MAX_TOKENS,
                temperature=settings.DEEPSEEK_TEMPERATURE,
                stream=False
            )
            answer = response.choices[0].message.content
            logger.info(f"回答生成完成，长度: {len(answer)} 字符")
            return answer
        except Exception as e:
            logger.error(f"DeepSeek API 调用失败: {e}")
            return f"抱歉，回答生成失败: {str(e)}"

    def generate_analysis(
        self,
        clause: str,
        contexts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        针对单条合同条款生成法律风险分析

        参数:
            clause: 合同条款文本
            contexts: 检索到的相关法条列表

        返回:
            包含 risk_level, risk_description, legal_basis, suggestion 的字典
        """
        context_text = self._build_context(contexts)

        system_prompt = (
            "你是一位专业的劳动合同法律顾问，擅长分析合同条款的法律风险。"
            "请严格按照 JSON 格式输出分析结果，不要输出其他任何内容。"
        )

        user_prompt = f"""请分析以下劳动合同条款的法律风险。

【相关法条参考】
{context_text}

【合同条款】
{clause}

请按以下 JSON 格式输出分析结果（不要输出 JSON 以外的内容）：
{{
    "risk_level": "低/中/高",
    "risk_description": "风险描述（详细说明该条款可能存在的法律问题）",
    "legal_basis": ["相关法律条款列表，如：劳动合同法第十九条"],
    "suggestion": "修改建议（给出具体的修改或补充建议）"
}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=settings.DEEPSEEK_MAX_TOKENS,
                temperature=0.1,  # 低温度确保输出稳定
                stream=False
            )
            content = response.choices[0].message.content.strip()
            # 尝试解析 JSON
            result = json.loads(content)
            return result
        except json.JSONDecodeError:
            logger.error(f"LLM 输出 JSON 解析失败，原始内容: {content}")
            return {
                "risk_level": "未知",
                "risk_description": "分析结果解析失败，建议人工审查该条款",
                "legal_basis": [],
                "suggestion": "建议人工审查该条款的法律合规性"
            }
        except Exception as e:
            logger.error(f"条款分析生成失败: {e}")
            return {
                "risk_level": "未知",
                "risk_description": f"分析失败: {str(e)}",
                "legal_basis": [],
                "suggestion": "建议人工审查该条款"
            }

    def split_clauses(self, contract_text: str) -> List[str]:
        """
        使用 LLM 将合同全文拆分为独立条款

        参数:
            contract_text: 合同全文

        返回:
            条款文本列表
        """
        system_prompt = (
            "你是一位合同分析专家。请将合同文本拆分为独立的条款，"
            "每条一行，以「条款N:」开头。"
        )

        user_prompt = f"""请将以下合同文本拆分为独立条款，每条一行：

{contract_text}

请按以下格式输出，每条一行：
条款1: xxx
条款2: xxx
..."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=settings.DEEPSEEK_MAX_TOKENS,
                temperature=0.1,
                stream=False
            )
            text = response.choices[0].message.content

            # 解析条款
            clauses = []
            for line in text.strip().split("\n"):
                line = line.strip()
                if line.startswith("条款"):
                    # 去掉 "条款N: " 前缀
                    parts = line.split(":", 1)
                    if len(parts) > 1:
                        clauses.append(parts[1].strip())
                    else:
                        clauses.append(line)

            # 如果解析失败，退回到简单换行分割
            if not clauses:
                clauses = [line.strip() for line in contract_text.split("\n") if line.strip()]

            logger.info(f"合同拆分完成，共 {len(clauses)} 条条款")
            return clauses

        except Exception as e:
            logger.error(f"条款拆分失败: {e}")
            # 退回到简单的换行分割
            return [line.strip() for line in contract_text.split("\n") if line.strip()]

    def _build_context(self, contexts: List[Dict[str, Any]]) -> str:
        """
        构建法条上下文文本

        将检索结果列表格式化为带编号的文本块
        """
        context_parts = []
        for i, ctx in enumerate(contexts, 1):
            law = ctx.get("law", "")
            article = ctx.get("article", "")
            content = ctx.get("content", "")
            context_parts.append(f"[{i}] {law} {article}\n{content}")
        return "\n\n".join(context_parts)

    def _default_system_prompt(self) -> str:
        """默认系统提示词"""
        return (
            "你是一位专业的劳动合同法律顾问，精通《劳动合同法》及相关劳动法规。"
            "请基于提供的法条内容，准确、专业地回答用户的劳动合同纠纷问题。\n"
            "回答时请：\n"
            "1. 明确引用相关法律条文（标明法律名称和条款编号）\n"
            "2. 用通俗语言解释法律含义\n"
            "3. 给出实用的维权建议\n"
            "4. 客观公正，不偏袒任何一方"
        )


# 全局单例
_generator = None


def get_generator() -> Generator:
    """获取全局 Generator 单例实例"""
    global _generator
    if _generator is None:
        _generator = Generator()
    return _generator
