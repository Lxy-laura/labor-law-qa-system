#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库初始化脚本

功能说明：
    1. 创建所有数据库表（users, documents, chunks, chat_history, feedback）
    2. 插入默认管理员账号（admin/admin123，密码已bcrypt加密存储）
    3. 插入真实法条数据（《劳动合同法》第19/20/37/39/46/47/87条原文）

使用的数据表结构：
    - users:         用户表（账号、密码哈希、角色等）
    - documents:     法律文档表（法律法规名称、发布日期等元数据）
    - chunks:        文档分块表（法条编号、原文、关键词等）
    - chat_history:   对话历史表（用户提问、AI回答、引用法条等）
    - feedback:       用户反馈表（回答是否有帮助、评分等）

使用方法：
    python scripts/init_db.py

环境变量（可在 .env 中配置）：
    DATABASE_URL=postgresql://labbor:labbor123@localhost:5432/labor_law
"""

import json
import os
import hashlib
import secrets
from pathlib import Path
from datetime import datetime

# ============================================================
# 配置区
# ============================================================

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 法条数据文件
SAMPLE_LAWS_FILE = PROJECT_ROOT / "data" / "sample_laws.json"

# 数据库配置（从环境变量读取，提供默认值）
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://labor:labor123@localhost:5432/labor_law",
)


# ============================================================
# 密码哈希工具函数
# ============================================================
def hash_password(password: str) -> str:
    """
    使用 PBKDF2-SHA256 对密码进行加盐哈希

    参数:
        password: 明文密码

    返回:
        格式为 "算法$迭代次数$盐$哈希值" 的字符串
    """
    salt = secrets.token_hex(16)  # 生成随机盐
    iterations = 100000
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations)
    hashed = dk.hex()
    return f"pbkdf2_sha256${iterations}${salt}${hashed}"


def verify_password(password: str, stored_hash: str) -> bool:
    """
    验证密码是否匹配存储的哈希值

    参数:
        password: 明文密码
        stored_hash: 存储的哈希字符串

    返回:
        是否匹配
    """
    try:
        algo, iterations, salt, hashed = stored_hash.split("$")
        iterations = int(iterations)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations)
        return secrets.compare_digest(dk.hex(), hashed)
    except Exception:
        return False


# ============================================================
# 建表 SQL 定义
# ============================================================

# 用户表
CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(64)  NOT NULL UNIQUE,
    password_hash   VARCHAR(256) NOT NULL,
    email           VARCHAR(128),
    role            VARCHAR(32)  NOT NULL DEFAULT 'user',
    phone           VARCHAR(32),
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE users IS '用户表';
COMMENT ON COLUMN users.role IS '角色：admin-管理员, user-普通用户';
"""

# 法律文档表
CREATE_DOCUMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS documents (
    id              SERIAL PRIMARY KEY,
    law_name        VARCHAR(256) NOT NULL,
    law_short_name  VARCHAR(128),
    issuing_authority VARCHAR(256),
    publish_date    DATE,
    effective_date  DATE,
    status          VARCHAR(32)  NOT NULL DEFAULT 'active',
    description     TEXT,
    created_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE documents IS '法律文档表';
COMMENT ON COLUMN documents.status IS '状态：active-有效, repealed-已废止, amended-已修订';
"""

# 文档分块表（法条级别）
CREATE_CHUNKS_TABLE = """
CREATE TABLE IF NOT EXISTS chunks (
    id              SERIAL PRIMARY KEY,
    document_id     INTEGER      NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    article_number  VARCHAR(32)  NOT NULL,
    article_no     INTEGER,
    title           VARCHAR(256),
    content         TEXT         NOT NULL,
    keywords        JSON,
    category        VARCHAR(64),
    chunk_index     INTEGER      NOT NULL DEFAULT 0,
    vector_id       VARCHAR(128),
    created_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE chunks IS '文档分块表（按法条粒度切分）';
COMMENT ON COLUMN chunks.vector_id IS 'Milvus向量库中对应的向量ID';
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_category ON chunks(category);
"""

# 对话历史表
CREATE_CHAT_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS chat_history (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER      REFERENCES users(id) ON DELETE SET NULL,
    session_id      VARCHAR(128),
    question        TEXT         NOT NULL,
    answer          TEXT         NOT NULL,
    retrieved_chunks JSON,
    confidence      REAL,
    feedback_status VARCHAR(32)  DEFAULT 'pending',
    created_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE chat_history IS '对话历史表';
COMMENT ON COLUMN chat_history.feedback_status IS '反馈状态：pending-待反馈, positive-正面, negative-负面';
"""

# 用户反馈表
CREATE_FEEDBACK_TABLE = """
CREATE TABLE IF NOT EXISTS feedback (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER      REFERENCES users(id) ON DELETE SET NULL,
    chat_id         INTEGER      REFERENCES chat_history(id) ON DELETE CASCADE,
    rating          SMALLINT     CHECK (rating >= 1 AND rating <= 5),
    comment         TEXT,
    feedback_type   VARCHAR(32)  NOT NULL DEFAULT 'general',
    created_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE feedback IS '用户反馈表';
COMMENT ON COLUMN feedback.feedback_type IS '反馈类型：general-通用, accuracy-准确性, relevance-相关性';
"""


def get_db_connection():
    """获取数据库连接"""
    import psycopg2

    # 从 DATABASE_URL 解析连接参数
    # 格式: postgresql://user:password@host:port/dbname
    url = DATABASE_URL.replace("postgresql://", "")
    # 简单解析
    auth_part, host_db = url.split("@")
    user_pass = auth_part
    host_port_db = host_db

    username, password = user_pass.split(":")
    host_port, dbname = host_port_db.split("/")
    host, port = host_port.split(":")

    conn = psycopg2.connect(
        host=host,
        port=int(port),
        dbname=dbname,
        user=username,
        password=password,
    )
    conn.autocommit = True
    return conn


def create_tables(conn):
    """创建所有数据库表"""
    cursor = conn.cursor()

    print("[信息] 开始创建数据库表...")

    tables = [
        ("users", CREATE_USERS_TABLE),
        ("documents", CREATE_DOCUMENTS_TABLE),
        ("chunks", CREATE_CHUNKS_TABLE),
        ("chat_history", CREATE_CHAT_HISTORY_TABLE),
        ("feedback", CREATE_FEEDBACK_TABLE),
    ]

    for table_name, sql in tables:
        cursor.execute(sql)
        print(f"  [完成] 创建表: {table_name}")

    cursor.close()
    print("[信息] 所有表创建完成！\n")


def insert_admin_user(conn):
    """插入默认管理员账号"""
    cursor = conn.cursor()

    # 检查是否已存在管理员账号
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    if cursor.fetchone():
        print("[信息] 管理员账号已存在，跳过插入")
        cursor.close()
        return

    # 生成密码哈希（admin123）
    password_hash = hash_password("admin123")

    cursor.execute(
        """
        INSERT INTO users (username, password_hash, email, role, phone, is_active)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            "admin",
            password_hash,
            "admin@labor-law-qa.local",
            "admin",
            None,
            True,
        ),
    )

    print("[完成] 默认管理员账号创建成功:")
    print(f"  用户名: admin")
    print(f"  密码:   admin123")
    print(f"  角色:   admin（管理员）")
    print(f"  [安全提示] 请在首次登录后立即修改默认密码！")

    cursor.close()


def insert_law_data(conn):
    """插入真实法条数据"""
    cursor = conn.cursor()

    # 加载法条数据
    with open(SAMPLE_LAWS_FILE, "r", encoding="utf-8") as f:
        laws_data = json.load(f)

    laws = laws_data.get("laws", [])
    print(f"\n[信息] 开始插入法条数据，共 {len(laws)} 条法条...")

    for law in laws:
        law_name = law["law_name"]
        law_short_name = law.get("law_short_name", law_name)
        article_number = law["article_number"]
        article_no = law.get("article_no", 0)
        title = law.get("title", "")
        content = law["content"]
        keywords = law.get("keywords", [])
        category = law.get("category", "")

        # 检查是否已插入该法条（避免重复插入）
        cursor.execute(
            """
            SELECT c.id FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE d.law_name = %s AND c.article_number = %s
            """,
            (law_name, article_number),
        )
        if cursor.fetchone():
            print(f"  [跳过] {law_short_name} {article_number} 已存在")
            continue

        # 插入或获取文档记录
        cursor.execute(
            """
            INSERT INTO documents (law_name, law_short_name, status, description)
            VALUES (%s, %s, 'active', %s)
            ON CONFLICT DO NOTHING
            RETURNING id
            """,
            (law_name, law_short_name, law.get("description", "")),
        )
        result = cursor.fetchone()
        if result:
            doc_id = result[0]
        else:
            # 文档已存在，获取其ID
            cursor.execute(
                "SELECT id FROM documents WHERE law_name = %s", (law_name,)
            )
            doc_id = cursor.fetchone()[0]

        # 插入法条分块记录
        cursor.execute(
            """
            INSERT INTO chunks (document_id, article_number, article_no, title, content, keywords, category)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (doc_id, article_number, article_no, title, content, json.dumps(keywords, ensure_ascii=False), category),
        )
        chunk_id = cursor.fetchone()[0]

        print(f"  [完成] {law_short_name} {article_number}（{title}）-> chunk_id={chunk_id}")

    cursor.close()
    print(f"\n[信息] 法条数据插入完成！共插入 {len(laws)} 条法条")


def main():
    """主函数：数据库初始化的完整流程"""
    print("=" * 60)
    print("数据库初始化")
    print("=" * 60)
    print(f"数据库连接: {DATABASE_URL}")

    # 获取数据库连接
    try:
        conn = get_db_connection()
        print("[信息] 数据库连接成功！\n")
    except Exception as e:
        print(f"\n[错误] 数据库连接失败: {e}")
        print("[提示] 请确认 PostgreSQL 已启动，且 .env 中 DATABASE_URL 配置正确")
        print(f"[提示] 可使用 docker-compose up -d postgres 启动数据库")
        return

    # 第一步：创建所有表
    create_tables(conn)

    # 第二步：插入默认管理员账号
    insert_admin_user(conn)

    # 第三步：插入真实法条数据
    insert_law_data(conn)

    # 关闭连接
    conn.close()

    print("\n" + "=" * 60)
    print("数据库初始化完成！")
    print("=" * 60)
    print("后续步骤:")
    print("  1. 运行 scripts/ingest_laws.py 将法条向量化并存入Milvus")
    print("  2. 运行 scripts/train_lora.py 训练语义模型")
    print("  3. 启动后端服务开始使用智能问答系统")


if __name__ == "__main__":
    main()
