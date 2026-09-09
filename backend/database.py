"""
劳动合同纠纷智能问答系统 - 数据库连接和初始化（SQLite 版本）

使用 SQLite 存储以下数据（SQLite 内置于 Python，无需安装）：
1. 用户表（users）- 用户账号和角色
2. 文档表（documents）- 知识库文档元数据
3. 对话历史表（chat_history）- 问答记录
4. 反馈表（feedback）- 用户对回答的评价
5. 研判记录表（judge_records）- 合同分析记录
"""
import os
import sqlite3
import logging
from config import settings

logger = logging.getLogger(__name__)

# SQLite 数据库文件路径
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "labor_law.db")

def get_connection():
    """获取 SQLite 数据库连接"""
    # check_same_thread=False 允许跨线程使用连接
    # FastAPI 同步端点在线程池中执行，必须关闭线程检查
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # 使查询结果可以通过列名访问
    return conn

def get_db():
    """
    FastAPI 依赖注入：获取数据库连接
    请求结束后自动关闭连接
    """
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """
    初始化数据库，创建所有需要的表
    在应用启动时调用
    """
    conn = get_connection()
    cur = conn.cursor()

    # ========== 1. 用户表 ==========
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            username        TEXT UNIQUE NOT NULL,
            email           TEXT UNIQUE NOT NULL,
            password_hash   TEXT NOT NULL,
            role            TEXT DEFAULT 'user',
            created_at      TEXT DEFAULT (datetime('now', 'localtime'))
        );
    """)

    # ========== 2. 文档表 ==========
    # 【修改点1】建表语句加了 file_size 和 indexed 字段
    cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            title           TEXT NOT NULL,
            content         TEXT NOT NULL,
            doc_type        TEXT,
            file_path       TEXT,
            file_size       INTEGER DEFAULT 0,
            chunk_count     INTEGER DEFAULT 0,
            indexed         INTEGER DEFAULT 0,
            uploaded_by     INTEGER REFERENCES users(id),
            created_at      TEXT DEFAULT (datetime('now', 'localtime'))
        );
    """)

    # 【修改点2】兼容旧数据库：如果 indexed 列不存在则自动添加
    try:
        cur.execute("SELECT indexed FROM documents LIMIT 1")
    except Exception:
        cur.execute("ALTER TABLE documents ADD COLUMN indexed INTEGER DEFAULT 0")
        logger.info("已为 documents 表添加 indexed 列")

    # 【修改点3】兼容旧数据库：如果 file_size 列不存在则自动添加
    try:
        cur.execute("SELECT file_size FROM documents LIMIT 1")
    except Exception:
        cur.execute("ALTER TABLE documents ADD COLUMN file_size INTEGER DEFAULT 0")
        logger.info("已为 documents 表添加 file_size 列")

    # ========== 3. 对话历史表 ==========
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER REFERENCES users(id),
            question        TEXT NOT NULL,
            answer          TEXT NOT NULL,
            citations       TEXT,
            confidence      REAL,
            is_favorited    INTEGER DEFAULT 0,
            created_at      TEXT DEFAULT (datetime('now', 'localtime'))
        );
    """)

    # 兼容旧数据库：如果 is_favorited 列不存在则添加
    try:
        cur.execute("SELECT is_favorited FROM chat_history LIMIT 1")
    except Exception:
        cur.execute("ALTER TABLE chat_history ADD COLUMN is_favorited INTEGER DEFAULT 0")
        logger.info("已为 chat_history 表添加 is_favorited 列")

    # ========== 4. 反馈表 ==========
    cur.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER REFERENCES users(id),
            chat_id         INTEGER REFERENCES chat_history(id),
            rating          INTEGER CHECK (rating IN (1, 2, 3, 4, 5)),
            comment         TEXT,
            created_at      TEXT DEFAULT (datetime('now', 'localtime'))
        );
    """)

    # ========== 5. 研判记录表 ==========
    cur.execute("""
        CREATE TABLE IF NOT EXISTS judge_records (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER REFERENCES users(id),
            contract_text   TEXT NOT NULL,
            analysis_result TEXT,
            created_at      TEXT DEFAULT (datetime('now', 'localtime'))
        );
    """)

    # 创建索引以提升查询性能
    cur.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_chat_history_user_id ON chat_history(user_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_chat_history_created_at ON chat_history(created_at DESC);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_feedback_chat_id ON feedback(chat_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_judge_records_user_id ON judge_records(user_id);")

    conn.commit()

    # ========== 创建默认管理员账号 ==========
    from auth.jwt_handler import hash_password
    cur.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
            ('admin', 'admin@system.com', hash_password('admin123'), 'admin')
        )
        cur.execute(
            "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
            ('testuser', 'test@system.com', hash_password('123456'), 'user')
        )
        conn.commit()
        logger.info("默认账号已创建: admin/admin123 (管理员), testuser/123456 (普通用户)")

    # ========== 确保管理员角色正确（兼容旧数据库）==========
    cur.execute("SELECT role FROM users WHERE username = 'admin'")
    admin_row = cur.fetchone()
    if admin_row and admin_row["role"] != 'admin':
        cur.execute("UPDATE users SET role = 'admin' WHERE username = 'admin'")
        conn.commit()
        logger.info("已修正 admin 用户角色为管理员")

    cur.close()
    conn.close()
    logger.info("SQLite 数据库初始化完成，所有表和索引已创建")