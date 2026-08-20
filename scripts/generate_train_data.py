#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
劳动法同义词训练数据自动生成脚本

功能说明：
    1. 从 data/legal_terms.json 加载200个劳动法术语词表
    2. 调用 DeepSeek API 为每个术语生成5个同义词及相似度评分
    3. 同时利用 data/synonym_dict.json 中已有的同义词映射进行补充
    4. 将生成的训练数据保存为 data/train_data.json

训练数据格式（Sentence-BERT 训练所需的句子对）：
    [
        {
            "term": "试用期",
            "synonym": "考察期",
            "similarity": 0.92,
            "label": 1  # 1=同义, 0=非同义（负样本）
        },
        ...
    ]

使用方法：
    export DEEPSEEK_API_KEY="your_api_key_here"
    python scripts/generate_train_data.py
"""

import json
import os
import time
import random
from pathlib import Path

# ============================================================
# 配置区
# ============================================================

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 数据文件路径
TERMS_FILE = PROJECT_ROOT / "data" / "legal_terms.json"
SYNONYM_DICT_FILE = PROJECT_ROOT / "data" / "synonym_dict.json"
OUTPUT_FILE = PROJECT_ROOT / "data" / "train_data.json"

# DeepSeek API 配置（使用 openai SDK 兼容接口）
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"

# 每个术语生成同义词的数量
SYNONYM_COUNT = 5

# 负样本比例（为每个正样本生成负样本对，用于对比学习）
NEGATIVE_RATIO = 1

# API 调用间隔（秒），避免触发限流
API_SLEEP_INTERVAL = 0.5


def load_terms():
    """加载劳动法术语词表"""
    with open(TERMS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    terms = data.get("terms", [])
    print(f"[信息] 已加载 {len(terms)} 个劳动法术语")
    return terms


def load_synonym_dict():
    """加载已有的同义词词典，用于补充训练数据"""
    with open(SYNONYM_DICT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    synonyms = data.get("synonyms", {})
    print(f"[信息] 已加载 {len(synonyms)} 个术语的同义词映射")
    return synonyms


def call_deepseek_api(term, api_key):
    """
    调用 DeepSeek API 为单个劳动法术语生成同义词

    参数:
        term: 劳动法术语
        api_key: DeepSeek API密钥

    返回:
        list: 包含同义词和相似度评分的列表，格式如:
            [{"synonym": "考察期", "similarity": 0.95}, ...]
    """
    from openai import OpenAI

    # 使用 openai SDK 连接 DeepSeek API
    client = OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)

    # 构造系统提示词，引导模型生成劳动法领域的同义词
    system_prompt = (
        "你是一位精通中国劳动法和劳动合同法的法律专家。"
        "你的任务是为给定的劳动法术语生成在日常生活中常用的同义词、俗称或近义表达。"
        "这些同义词应该是在劳动争议中当事人可能使用的非正式表达。"
    )

    # 构造用户提示词，要求模型返回JSON格式
    user_prompt = (
        f'请为劳动法术语"{term}"生成{SYNONYM_COUNT}个在劳动争议中常用的同义词、俗称或近义表达。\n'
        f"要求：\n"
        f"1. 每个同义词必须是在劳动争议中真实使用的表达\n"
        f"2. 为每个同义词给出0到1之间的语义相似度评分（1表示完全同义）\n"
        f"3. 请严格按照以下JSON格式返回，不要包含其他内容：\n"
        f'{{"synonyms": [{{"synonym": "同义词1", "similarity": 0.95}}, ...]}}\n'
    )

    try:
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,  # 适度随机，保证生成多样性
            max_tokens=500,
        )

        # 解析返回内容
        content = response.choices[0].message.content.strip()

        # 尝试提取JSON部分（模型可能在JSON前后添加额外文字）
        json_start = content.find("{")
        json_end = content.rfind("}") + 1
        if json_start == -1 or json_end == 0:
            print(f"  [警告] 术语 '{term}' 的API返回无法解析JSON: {content[:100]}")
            return []

        json_str = content[json_start:json_end]
        result = json.loads(json_str)

        synonyms = result.get("synonyms", [])
        print(f"  [成功] 术语 '{term}' 生成了 {len(synonyms)} 个同义词")
        return synonyms

    except json.JSONDecodeError as e:
        print(f"  [错误] 术语 '{term}' JSON解析失败: {e}")
        return []
    except Exception as e:
        print(f"  [错误] 术语 '{term}' API调用失败: {e}")
        return []


def build_training_pairs(terms, api_synonyms, synonym_dict):
    """
    构建训练数据对（正样本+负样本）

    参数:
        terms: 劳动法术语列表
        api_synonyms: DeepSeek API生成的同义词映射 {term: [{synonym, similarity}]}
        synonym_dict: 本地同义词词典 {term: [synonym1, synonym2, ...]}

    返回:
        list: 训练数据对列表
    """
    train_data = []

    # ---------- 生成正样本 ----------
    for term in terms:
        # 来源1: DeepSeek API 生成的同义词
        api_syn_list = api_synonyms.get(term, [])
        for item in api_syn_list:
            synonym = item.get("synonym", "").strip()
            similarity = float(item.get("similarity", 0.8))
            if synonym and synonym != term:
                train_data.append(
                    {
                        "term": term,
                        "synonym": synonym,
                        "similarity": similarity,
                        "label": 1,
                        "source": "deepseek_api",
                    }
                )

        # 来源2: 本地同义词词典中的映射
        local_syn_list = synonym_dict.get(term, [])
        for synonym in local_syn_list:
            synonym = synonym.strip()
            if synonym and synonym != term:
                # 避免与API生成的重复
                exists = any(
                    d["synonym"] == synonym for d in train_data if d["term"] == term
                )
                if not exists:
                    train_data.append(
                        {
                            "term": term,
                            "synonym": synonym,
                            "similarity": 0.90,  # 本地词典中的映射给予较高的相似度
                            "label": 1,
                            "source": "local_dict",
                        }
                    )

    # ---------- 生成负样本 ----------
    # 随机配对不同术语作为负样本，相似度设为较低值
    positive_count = len(train_data)
    negative_count = int(positive_count * NEGATIVE_RATIO)

    all_terms = list(set(terms))
    for _ in range(negative_count):
        # 随机选取两个不相关的术语作为负样本对
        term_a = random.choice(all_terms)
        term_b = random.choice(all_terms)
        if term_a != term_b:
            # 确保不是已存在的同义对
            is_synonym = any(
                (d["term"] == term_a and d["synonym"] == term_b)
                or (d["term"] == term_b and d["synonym"] == term_a)
                for d in train_data
            )
            if not is_synonym:
                train_data.append(
                    {
                        "term": term_a,
                        "synonym": term_b,
                        "similarity": round(random.uniform(0.05, 0.25), 2),
                        "label": 0,
                        "source": "random_negative",
                    }
                )

    print(f"[信息] 共生成训练数据对: {len(train_data)} 条")
    print(f"  - 正样本: {sum(1 for d in train_data if d['label'] == 1)} 条")
    print(f"  - 负样本: {sum(1 for d in train_data if d['label'] == 0)} 条")
    return train_data


def save_train_data(train_data):
    """保存训练数据到JSON文件"""
    output = {
        "description": "劳动法同义词训练数据，用于Sentence-BERT LoRA微调",
        "total_pairs": len(train_data),
        "positive_samples": sum(1 for d in train_data if d["label"] == 1),
        "negative_samples": sum(1 for d in train_data if d["label"] == 0),
        "data": train_data,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[完成] 训练数据已保存到: {OUTPUT_FILE}")
    print(f"  - 总数据对数: {output['total_pairs']}")
    print(f"  - 正样本: {output['positive_samples']}")
    print(f"  - 负样本: {output['negative_samples']}")


def main():
    """主函数：生成训练数据的完整流程"""
    print("=" * 60)
    print("劳动法同义词训练数据自动生成")
    print("=" * 60)

    # 第一步：加载术语词表和同义词词典
    terms = load_terms()
    synonym_dict = load_synonym_dict()

    # 第二步：获取DeepSeek API密钥
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("\n[警告] 未检测到 DEEPSEEK_API_KEY 环境变量！")
        print("[提示] 将仅使用本地同义词词典生成训练数据。")
        print("[提示] 如需使用DeepSeek API生成更丰富的数据，请设置环境变量：")
        print("  export DEEPSEEK_API_KEY='your_api_key_here'")
        api_synonyms = {}
    else:
        print(f"\n[信息] 检测到 DeepSeek API密钥，开始为 {len(terms)} 个术语生成同义词...")

        # 第三步：调用DeepSeek API为每个术语生成同义词
        api_synonyms = {}
        for i, term in enumerate(terms, 1):
            print(f"\n[{i}/{len(terms)}] 正在处理术语: {term}")
            synonyms = call_deepseek_api(term, api_key)
            if synonyms:
                api_synonyms[term] = synonyms
            # API调用间隔，避免触发限流
            time.sleep(API_SLEEP_INTERVAL)

        print(f"\n[信息] API生成完成，共为 {len(api_synonyms)} 个术语生成了同义词")

    # 第四步：构建训练数据对（正样本+负样本）
    print("\n[信息] 开始构建训练数据对...")
    train_data = build_training_pairs(terms, api_synonyms, synonym_dict)

    # 第五步：保存训练数据
    save_train_data(train_data)

    print("\n" + "=" * 60)
    print("训练数据生成完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
