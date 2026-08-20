"""
劳动合同纠纷智能问答系统 - 同义词扩展器

功能：
1. 加载劳动法术语同义词词典（JSON 格式）
2. 可选加载 LoRA 微调模型进行语义扩展
3. 对用户查询进行术语扩展，提升检索召回率

策略：
- 基于词典：遍历同义词词典，如果查询包含某术语，追加其同义词
- 基于 LoRA：使用微调模型生成语义相关的扩展词（可选）
"""
import json
import logging
from typing import List
from config import settings

logger = logging.getLogger(__name__)


class SynonymExpander:
    """
    同义词扩展器

    通过术语词典和（可选）LoRA 微调模型对查询进行同义词扩展，
    将 "被辞退了怎么办" 扩展为 "被辞退了怎么办 解雇 开除 解除劳动合同 终止劳动关系"
    """

    def __init__(self):
        """初始化同义词扩展器"""
        self.synonym_dict = {}     # 同义词词典
        self.lora_model = None     # LoRA 微调模型
        self.lora_tokenizer = None

        # 加载同义词词典
        self._load_synonym_dict()

        # 加载 LoRA 微调模型（可选）
        if settings.LORA_MODEL_PATH:
            self._load_lora_model()

    def _load_synonym_dict(self):
        """
        加载同义词词典 JSON 文件

        词典格式：
        {
            "辞退": ["解雇", "开除", "解除劳动合同", "终止劳动关系"],
            "赔偿金": ["经济补偿", "补偿金", "遣散费"],
            ...
        }
        """
        try:
            with open(settings.SYNONYM_DICT_PATH, "r", encoding="utf-8") as f:
                self.synonym_dict = json.load(f)
            logger.info(f"同义词词典加载成功，共 {len(self.synonym_dict)} 组术语")
        except Exception as e:
            logger.warning(f"同义词词典加载失败: {e}")
            self.synonym_dict = {}

    def _load_lora_model(self):
        """
        加载 LoRA 微调模型用于语义扩展

        使用 PEFT 库加载 LoRA adapter 到基础语言模型上，
        用于生成与查询语义相关的扩展词
        """
        try:
            from peft import PeftModel, PeftConfig
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch

            # 加载 LoRA 配置和基础模型
            peft_config = PeftConfig.from_pretrained(settings.LORA_MODEL_PATH)
            base_model = AutoModelForCausalLM.from_pretrained(
                peft_config.base_model_name_or_path,
                torch_dtype=torch.float16,
                device_map="auto"
            )
            # 加载 LoRA adapter
            self.lora_model = PeftModel.from_pretrained(base_model, settings.LORA_MODEL_PATH)
            self.lora_tokenizer = AutoTokenizer.from_pretrained(
                peft_config.base_model_name_or_path
            )
            logger.info("LoRA 微调模型加载成功")
        except Exception as e:
            logger.warning(f"LoRA 微调模型加载失败，仅使用词典扩展: {e}")
            self.lora_model = None

    def expand(self, query: str) -> str:
        """
        扩展查询：在原始查询基础上补充同义词

        策略：
        1. 遍历同义词词典，检查查询中是否包含关键术语
        2. 如果包含，将同义词追加到查询中
        3. 如果有 LoRA 模型，使用模型生成语义相关的扩展词

        参数:
            query: 用户原始查询

        返回:
            扩展后的查询字符串
        """
        expanded_terms = []

        # ========== 基于词典的扩展 ==========
        for key, synonyms in self.synonym_dict.items():
            if key in query:
                for syn in synonyms:
                    if syn not in query and syn not in expanded_terms:
                        expanded_terms.append(syn)

        # ========== 基于 LoRA 模型的语义扩展 ==========
        if self.lora_model is not None:
            lora_expansions = self._lora_expand(query)
            for term in lora_expansions:
                if term not in query and term not in expanded_terms:
                    expanded_terms.append(term)

        # 构建扩展查询（最多追加5个同义词，避免查询过长）
        if expanded_terms:
            expanded_query = f"{query} {' '.join(expanded_terms[:5])}"
            logger.info(f"查询扩展: '{query}' -> '{expanded_query}'")
            return expanded_query
        else:
            logger.info(f"查询无需扩展: '{query}'")
            return query

    def _lora_expand(self, query: str) -> List[str]:
        """
        使用 LoRA 微调模型生成语义扩展词

        参数:
            query: 用户查询

        返回:
            扩展词列表
        """
        try:
            import torch

            prompt = (
                f"请为以下劳动法问题生成3个相关的同义词或近义词，用逗号分隔：\n"
                f"{query}\n同义词："
            )
            inputs = self.lora_tokenizer(prompt, return_tensors="pt")

            with torch.no_grad():
                outputs = self.lora_model.generate(
                    **inputs,
                    max_new_tokens=50,
                    temperature=0.7,
                    do_sample=True
                )

            generated = self.lora_tokenizer.decode(outputs[0], skip_special_tokens=True)

            # 提取生成的同义词部分
            result_part = generated.split("同义词：")[-1].strip()
            terms = [t.strip() for t in result_part.split("，") if t.strip()]
            return terms[:3]
        except Exception as e:
            logger.error(f"LoRA 语义扩展失败: {e}")
            return []

    def get_synonyms(self, term: str) -> List[str]:
        """
        获取某个术语的同义词列表

        参数:
            term: 术语

        返回:
            同义词列表
        """
        return self.synonym_dict.get(term, [])


# 全局单例
_expander = None


def get_expander() -> SynonymExpander:
    """获取全局 SynonymExpander 单例实例"""
    global _expander
    if _expander is None:
        _expander = SynonymExpander()
    return _expander
