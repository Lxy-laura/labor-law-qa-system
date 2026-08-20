#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sentence-BERT LoRA 微调脚本

功能说明：
    1. 加载预训练模型 BAAI/bge-large-zh-v1.5
    2. 使用 PEFT 库配置 LoRA（低秩自适应）微调参数
    3. 加载 data/train_data.json 训练数据
    4. 使用 CosineSimilarityLoss（余弦相似度损失）训练3个epoch
    5. 保存微调后的模型到 models/legal-lora-model/
    6. 打印训练前后相似度对比

技术栈：
    - sentence-transformers: 句向量模型库
    - peft: 参数高效微调（LoRA）
    - transformers: Hugging Face 模型加载
    - torch: 深度学习框架

使用方法：
    python scripts/train_lora.py
"""

import json
import os
import torch
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple

# ============================================================
# 配置区
# ============================================================

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 训练数据文件
TRAIN_DATA_FILE = PROJECT_ROOT / "data" / "train_data.json"

# 模型保存路径
MODEL_SAVE_PATH = PROJECT_ROOT / "models" / "legal-lora-model"

# 预训练模型名称
PRETRAINED_MODEL = "BAAI/bge-large-zh-v1.5"

# LoRA 配置参数
LORA_R = 8                # LoRA 秩
LORA_ALPHA = 16            # LoRA 缩放因子
LORA_DROPOUT = 0.05        # LoRA Dropout 比率
LORA_TARGET_MODULES = ["query", "value"]  # LoRA 目标模块

# 训练超参数
EPOCHS = 3                 # 训练轮次
BATCH_SIZE = 16            # 批次大小
LEARNING_RATE = 2e-5       # 学习率
WARMUP_RATIO = 0.1          # 预热比例
MAX_SEQUENCE_LENGTH = 128   # 最大序列长度


def load_train_data() -> List[Dict]:
    """
    加载训练数据

    返回:
        训练数据列表，每条数据包含 term, synonym, similarity 等字段
    """
    with open(TRAIN_DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    train_pairs = data.get("data", [])
    print(f"[信息] 加载训练数据: {len(train_pairs)} 条")
    print(f"  - 正样本: {data.get('positive_samples', 0)} 条")
    print(f"  - 负样本: {data.get('negative_samples', 0)} 条")
    return train_pairs


def compute_similarity(
    model, sentences1: List[str], sentences2: List[str]
) -> np.ndarray:
    """
    使用模型计算两组句子的余弦相似度矩阵

    参数:
        model: SentenceTransformer 模型
        sentences1: 第一组句子列表
        sentences2: 第二组句子列表

    返回:
        相似度矩阵 (N x N)
    """
    # 编码句子为向量
    embeddings1 = model.encode(sentences1, convert_to_tensor=True, normalize_embeddings=True)
    embeddings2 = model.encode(sentences2, convert_to_tensor=True, normalize_embeddings=True)

    # 计算余弦相似度矩阵
    similarity_matrix = torch.mm(embeddings1, embeddings2.T)
    return similarity_matrix.cpu().numpy()


def evaluate_before_training(
    model, train_pairs: List[Dict], sample_size: int = 50
) -> Tuple[float, float, float]:
    """
    训练前评估模型在术语对上的相似度表现

    参数:
        model: SentenceTransformer 模型
        train_pairs: 训练数据对
        sample_size: 采样评估的样本数

    返回:
        (正样本平均相似度, 负样本平均相似度, 区分度)
    """
    # 随机采样评估
    import random
    random.seed(42)
    sample = random.sample(train_pairs, min(sample_size, len(train_pairs)))

    pos_pairs = [(d["term"], d["synonym"]) for d in sample if d["label"] == 1]
    neg_pairs = [(d["term"], d["synonym"]) for d in sample if d["label"] == 0]

    pos_scores = []
    for term, syn in pos_pairs:
        sim = compute_similarity(model, [term], [syn])[0][0]
        pos_scores.append(sim)

    neg_scores = []
    for term, syn in neg_pairs:
        sim = compute_similarity(model, [term], [syn])[0][0]
        neg_scores.append(sim)

    pos_avg = np.mean(pos_scores) if pos_scores else 0.0
    neg_avg = np.mean(neg_scores) if neg_scores else 0.0
    margin = pos_avg - neg_avg

    return pos_avg, neg_avg, margin


def train_with_lora(train_pairs: List[Dict]):
    """
    使用 LoRA 微调 Sentence-BERT 模型

    参数:
        train_pairs: 训练数据对列表

    返回:
        训练后的模型
    """
    from sentence_transformers import SentenceTransformer
    from peft import LoraConfig, get_peft_model
    from sentence_transformers import losses, InputExample
    from torch.utils.data import DataLoader

    print(f"\n[信息] 正在加载预训练模型: {PRETRAINED_MODEL}")
    print("[信息] 首次运行会从HuggingFace下载模型，请耐心等待...")

    # 加载预训练的 Sentence-BERT 模型
    model = SentenceTransformer(PRETRAINED_MODEL)
    # 设置最大序列长度
    model.max_seq_length = MAX_SEQUENCE_LENGTH

    print(f"[信息] 模型加载完成，最大序列长度: {MAX_SEQUENCE_LENGTH}")

    # ============================================================
    # 训练前评估
    # ============================================================
    print("\n" + "=" * 60)
    print("训练前模型评估")
    print("=" * 60)
    pos_before, neg_before, margin_before = evaluate_before_training(model, train_pairs)
    print(f"  正样本平均相似度: {pos_before:.4f}")
    print(f"  负样本平均相似度: {neg_before:.4f}")
    print(f"  区分度(正-负):    {margin_before:.4f}")

    # ============================================================
    # 配置 LoRA 微调
    # ============================================================
    print(f"\n[信息] 配置 LoRA 微调参数:")
    print(f"  - LoRA rank (r): {LORA_R}")
    print(f"  - LoRA alpha:    {LORA_ALPHA}")
    print(f"  - LoRA dropout:  {LORA_DROPOUT}")
    print(f"  - 目标模块:      {LORA_TARGET_MODULES}")

    # 获取底层的 Transformer 模型
    transformer_model = model[0].auto_model  # 获取第一层（Transformer层）的底层模型

    # 配置 LoRA
    lora_config = LoraConfig(
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        target_modules=LORA_TARGET_MODULES,
        bias="none",
        task_type="FEATURE_EXTRACTION",  # 特征提取任务类型
    )

    # 将 LoRA 配置应用到模型上
    transformer_model = get_peft_model(transformer_model, lora_config)
    # 将修改后的 Transformer 模型放回 SentenceTransformer
    model[0].auto_model = transformer_model

    # 打印可训练参数量
    transformer_model.print_trainable_parameters()

    # ============================================================
    # 准备训练数据
    # ============================================================
    print(f"\n[信息] 准备训练数据...")
    # 构建训练样本（InputExample 格式）
    train_examples = []
    for pair in train_pairs:
        term = pair["term"]
        synonym = pair["synonym"]
        similarity = pair["similarity"]
        # CosineSimilarityLoss 需要的标签为相似度值（0~1之间）
        train_examples.append(InputExample(texts=[term, synonym], label=similarity))

    # 创建数据加载器
    train_dataloader = DataLoader(
        train_examples,
        shuffle=True,
        batch_size=BATCH_SIZE,
    )

    # 使用余弦相似度损失函数
    train_loss = losses.CosineSimilarityLoss(model=model)

    # ============================================================
    # 开始训练
    # ============================================================
    print(f"\n[信息] 开始 LoRA 微调训练:")
    print(f"  - 训练轮次 (epochs): {EPOCHS}")
    print(f"  - 批次大小 (batch_size): {BATCH_SIZE}")
    print(f"  - 学习率 (learning_rate): {LEARNING_RATE}")
    print(f"  - 预热比例 (warmup_ratio): {WARMUP_RATIO}")
    print(f"  - 损失函数: CosineSimilarityLoss")
    print("-" * 60)

    # 使用 SentenceTransformer 的 fit 方法进行训练
    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=EPOCHS,
        warmup_steps=int(len(train_dataloader) * EPOCHS * WARMUP_RATIO),
        optimizer_params={"lr": LEARNING_RATE},
        show_progress_bar=True,
    )

    print("-" * 60)
    print("[信息] 训练完成！")

    # ============================================================
    # 训练后评估
    # ============================================================
    print("\n" + "=" * 60)
    print("训练后模型评估")
    print("=" * 60)
    pos_after, neg_after, margin_after = evaluate_before_training(model, train_pairs)
    print(f"  正样本平均相似度: {pos_after:.4f}")
    print(f"  负样本平均相似度: {neg_after:.4f}")
    print(f"  区分度(正-负):    {margin_after:.4f}")

    # ============================================================
    # 训练前后对比
    # ============================================================
    print("\n" + "=" * 60)
    print("训练前后相似度对比")
    print("=" * 60)
    print(f"{'指标':<20} {'训练前':<15} {'训练后':<15} {'提升':<15}")
    print("-" * 60)
    print(f"{'正样本相似度':<20} {pos_before:<15.4f} {pos_after:<15.4f} {pos_after - pos_before:+.4f}")
    print(f"{'负样本相似度':<20} {neg_before:<15.4f} {neg_after:<15.4f} {neg_after - neg_before:+.4f}")
    print(f"{'区分度':<20} {margin_before:<15.4f} {margin_after:<15.4f} {margin_after - margin_before:+.4f}")
    print("-" * 60)

    # ============================================================
    # 保存模型
    # ============================================================
    print(f"\n[信息] 保存微调后的模型到: {MODEL_SAVE_PATH}")
    MODEL_SAVE_PATH.mkdir(parents=True, exist_ok=True)
    model.save(str(MODEL_SAVE_PATH))
    print("[完成] 模型保存成功！")

    return model


def main():
    """主函数：LoRA 微调的完整流程"""
    print("=" * 60)
    print("Sentence-BERT LoRA 微调（劳动法同义词）")
    print("=" * 60)

    # 检查训练数据是否存在
    if not TRAIN_DATA_FILE.exists():
        print(f"\n[错误] 训练数据文件不存在: {TRAIN_DATA_FILE}")
        print("[提示] 请先运行 scripts/generate_train_data.py 生成训练数据")
        return

    # 第一步：加载训练数据
    train_pairs = load_train_data()
    if not train_pairs:
        print("[错误] 训练数据为空，请检查数据文件")
        return

    # 第二步：LoRA 微调训练
    model = train_with_lora(train_pairs)

    print("\n" + "=" * 60)
    print("LoRA 微调完成！")
    print("=" * 60)
    print(f"模型保存路径: {MODEL_SAVE_PATH}")
    print(f"可使用 scripts/eval_model.py 进行详细评估")


if __name__ == "__main__":
    main()
