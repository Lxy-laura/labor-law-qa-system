#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型评估脚本

功能说明：
    1. 加载微调前（原始 BAAI/bge-large-zh-v1.5）和微调后（LoRA）的模型
    2. 对预设的测试术语对计算余弦相似度
    3. 输出对比表格，直观展示微调效果

使用方法：
    python scripts/eval_model.py
"""

import torch
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
import time

# ============================================================
# 配置区
# ============================================================

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 预训练模型名称
PRETRAINED_MODEL = "BAAI/bge-large-zh-v1.5"

# 微调后的模型路径
FINETUNED_MODEL_PATH = PROJECT_ROOT / "models" / "legal-lora-model"

# ============================================================
# 测试术语对（包含正样本对和负样本对）
# 正样本：同义/近义的劳动法术语对
# 负样本：语义不同的术语对
# ============================================================
TEST_PAIRS = [
    # ===== 正样本（同义词对）=====
    {"term1": "试用期", "term2": "考察期", "expected": "high", "note": "同义词"},
    {"term1": "辞退", "term2": "解除劳动合同", "expected": "high", "note": "同义词"},
    {"term1": "加班费", "term2": "延时工资", "expected": "high", "note": "同义词"},
    {"term1": "竞业限制", "term2": "竞业禁止", "expected": "high", "note": "同义词"},
    {"term1": "经济补偿", "term2": "离职补偿", "expected": "high", "note": "同义词"},
    {"term1": "违法解除", "term2": "非法辞退", "expected": "high", "note": "同义词"},
    {"term1": "二倍工资", "term2": "双倍工资", "expected": "high", "note": "同义词"},
    {"term1": "押金", "term2": "保证金", "expected": "high", "note": "同义词"},
    {"term1": "社保", "term2": "社会保险", "expected": "high", "note": "同义词"},
    {"term1": "拖欠工资", "term2": "欠薪", "expected": "high", "note": "同义词"},
    {"term1": "劳务派遣", "term2": "人力派遣", "expected": "high", "note": "同义词"},
    {"term1": "非全日制用工", "term2": "小时工", "expected": "high", "note": "同义词"},
    {"term1": "调岗", "term2": "岗位调整", "expected": "high", "note": "同义词"},
    {"term1": "年休假", "term2": "带薪年假", "expected": "high", "note": "同义词"},
    {"term1": "工伤", "term2": "因工受伤", "expected": "high", "note": "同义词"},

    # ===== 负样本（语义不同的术语对）=====
    {"term1": "试用期", "term2": "经济补偿", "expected": "low", "note": "不同概念"},
    {"term1": "竞业限制", "term2": "加班费", "expected": "low", "note": "不同概念"},
    {"term1": "二倍工资", "term2": "竞业限制", "expected": "low", "note": "不同概念"},
    {"term1": "社保", "term2": "工伤认定", "expected": "low", "note": "不同概念"},
    {"term1": "劳务派遣", "term2": "经济性裁员", "expected": "low", "note": "不同概念"},
    {"term1": "年休假", "term2": "竞业限制协议", "expected": "low", "note": "不同概念"},
    {"term1": "调岗", "term2": "社会保险费", "expected": "low", "note": "不同概念"},
    {"term1": "押金", "term2": "劳动仲裁", "expected": "low", "note": "不同概念"},
    {"term1": "违法解除", "term2": "年休假", "expected": "low", "note": "不同概念"},
    {"term1": "工伤", "term2": "二倍工资", "expected": "low", "note": "不同概念"},
]


def load_model(model_path: str, use_finetuned: bool = False) -> "SentenceTransformer":
    """
    加载 SentenceTransformer 模型

    参数:
        model_path: 模型路径或名称
        use_finetuned: 是否为微调后的模型

    返回:
        SentenceTransformer 模型实例
    """
    from sentence_transformers import SentenceTransformer

    if use_finetuned:
        print(f"[信息] 加载微调后的模型: {model_path}")
    else:
        print(f"[信息] 加载原始预训练模型: {model_path}")

    model = SentenceTransformer(model_path)
    model.max_seq_length = 128
    return model


def compute_pair_similarity(model, term1: str, term2: str) -> float:
    """
    计算两个术语之间的余弦相似度

    参数:
        model: SentenceTransformer 模型
        term1: 术语1
        term2: 术语2

    返回:
        余弦相似度 (0~1)
    """
    # 编码为向量（归一化后直接点积即为余弦相似度）
    emb1 = model.encode([term1], convert_to_tensor=True, normalize_embeddings=True)
    emb2 = model.encode([term2], convert_to_tensor=True, normalize_embeddings=True)

    # 计算余弦相似度
    similarity = torch.mm(emb1, emb2.T).cpu().numpy()[0][0]
    return float(similarity)


def evaluate_model(model, test_pairs: List[Dict]) -> Tuple[float, float]:
    """
    评估模型在测试术语对上的表现

    参数:
        model: SentenceTransformer 模型
        test_pairs: 测试术语对列表

    返回:
        (正样本平均相似度, 负样本平均相似度)
    """
    results = []
    pos_scores = []
    neg_scores = []

    for pair in test_pairs:
        sim = compute_pair_similarity(model, pair["term1"], pair["term2"])
        results.append(
            {
                "term1": pair["term1"],
                "term2": pair["term2"],
                "similarity": sim,
                "expected": pair["expected"],
                "note": pair["note"],
            }
        )
        if pair["expected"] == "high":
            pos_scores.append(sim)
        else:
            neg_scores.append(sim)

    pos_avg = np.mean(pos_scores) if pos_scores else 0.0
    neg_avg = np.mean(neg_scores) if neg_scores else 0.0

    return results, pos_avg, neg_avg


def print_comparison_table(
    results_before: List[Dict],
    results_after: List[Dict],
):
    """
    打印微调前后的相似度对比表格

    参数:
        results_before: 微调前的评估结果
        results_after: 微调后的评估结果
    """
    print("\n" + "=" * 100)
    print("模型微调前后相似度对比表格")
    print("=" * 100)

    # 表头
    header = f"{'术语1':<12} {'术语2':<16} {'期望':<6} {'微调前':<10} {'微调后':<10} {'变化':<10} {'备注'}"
    print(header)
    print("-" * 100)

    # 数据行
    for rb, ra in zip(results_before, results_after):
        expected_str = "高" if rb["expected"] == "high" else "低"
        before_sim = rb["similarity"]
        after_sim = ra["similarity"]
        change = after_sim - before_sim
        change_str = f"{change:+.4f}"

        # 根据变化情况标注
        if rb["expected"] == "high" and change > 0:
            tag = "改善"
        elif rb["expected"] == "low" and change < 0:
            tag = "改善"
        elif rb["expected"] == "high" and change < 0:
            tag = "需关注"
        elif rb["expected"] == "low" and change > 0:
            tag = "需关注"
        else:
            tag = "-"

        print(
            f"{rb['term1']:<12} {rb['term2']:<16} {expected_str:<6} "
            f"{before_sim:<10.4f} {after_sim:<10.4f} {change_str:<10} "
            f"{rb['note']} [{tag}]"
        )

    print("-" * 100)


def print_summary(pos_before, neg_before, pos_after, neg_after):
    """打印汇总统计"""
    print("\n" + "=" * 60)
    print("汇总统计")
    print("=" * 60)

    margin_before = pos_before - neg_before
    margin_after = pos_after - neg_after

    print(f"{'指标':<25} {'微调前':<15} {'微调后':<15} {'变化':<15}")
    print("-" * 60)
    print(f"{'正样本平均相似度':<25} {pos_before:<15.4f} {pos_after:<15.4f} {pos_after - pos_before:+.4f}")
    print(f"{'负样本平均相似度':<25} {neg_before:<15.4f} {neg_after:<15.4f} {neg_after - neg_before:+.4f}")
    print(f"{'区分度(正-负)':<25} {margin_before:<15.4f} {margin_after:<15.4f} {margin_after - margin_before:+.4f}")
    print("-" * 60)

    # 判断微调效果
    if margin_after > margin_before:
        print("\n[结论] 微调有效！模型区分度提升了 "
              f"{margin_after - margin_before:.4f}，同义词召回能力增强。")
    else:
        print("\n[结论] 微调效果不明显，建议调整训练参数或增加训练数据。")


def main():
    """主函数：模型评估的完整流程"""
    print("=" * 60)
    print("Sentence-BERT 模型评估（微调前后对比）")
    print("=" * 60)

    # 第一步：加载原始预训练模型
    model_before = load_model(PRETRAINED_MODEL, use_finetuned=False)

    # 第二步：加载微调后的模型
    if not FINETUNED_MODEL_PATH.exists():
        print(f"\n[警告] 微调后的模型路径不存在: {FINETUNED_MODEL_PATH}")
        print("[提示] 请先运行 scripts/train_lora.py 进行LoRA微调")
        print("[提示] 本次仅评估原始模型的表现\n")

        # 仅评估原始模型
        results_before, pos_before, neg_before = evaluate_model(model_before, TEST_PAIRS)
        print(f"\n原始模型评估结果:")
        print(f"  正样本平均相似度: {pos_before:.4f}")
        print(f"  负样本平均相似度: {neg_before:.4f}")
        print(f"  区分度: {pos_before - neg_before:.4f}")
        return

    model_after = load_model(str(FINETUNED_MODEL_PATH), use_finetuned=True)

    # 第三步：分别评估两个模型
    print(f"\n[信息] 共 {len(TEST_PAIRS)} 个测试术语对")
    print(f"  - 正样本（同义词对）: {sum(1 for p in TEST_PAIRS if p['expected'] == 'high')} 个")
    print(f"  - 负样本（不同概念）: {sum(1 for p in TEST_PAIRS if p['expected'] == 'low')} 个")

    print("\n[信息] 正在评估原始预训练模型...")
    t0 = time.time()
    results_before, pos_before, neg_before = evaluate_model(model_before, TEST_PAIRS)
    print(f"  耗时: {time.time() - t0:.2f}s")

    print("\n[信息] 正在评估微调后模型...")
    t0 = time.time()
    results_after, pos_after, neg_after = evaluate_model(model_after, TEST_PAIRS)
    print(f"  耗时: {time.time() - t0:.2f}s")

    # 第四步：打印对比表格
    print_comparison_table(results_before, results_after)

    # 第五步：打印汇总统计
    print_summary(pos_before, neg_before, pos_after, neg_after)

    print("\n" + "=" * 60)
    print("模型评估完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
