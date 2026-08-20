"""
劳动合同纠纷智能问答系统 - JWT Token 处理

负责：
1. 密码哈希与验证（使用 PBKDF2 + SHA256）
2. JWT Token 生成（包含用户ID、用户名、角色、过期时间）
3. JWT Token 验证与解码
"""
import jwt
import hashlib
import os
import time
import logging
from config import settings

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """
    使用 PBKDF2-HMAC-SHA256 对密码进行加盐哈希

    参数:
        password: 明文密码

    返回:
        格式为 "salt_hex:key_hex" 的哈希字符串
    """
    # 生成随机盐值（32字节）
    salt = os.urandom(32)
    # 使用 PBKDF2 派生密钥（迭代10万次）
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000  # 迭代次数，增加暴力破解难度
    )
    return salt.hex() + ':' + key.hex()


def verify_password(password: str, stored_hash: str) -> bool:
    """
    验证明文密码是否与存储的哈希匹配

    参数:
        password: 用户输入的明文密码
        stored_hash: 数据库中存储的哈希值

    返回:
        是否匹配
    """
    try:
        salt_hex, key_hex = stored_hash.split(':')
        salt = bytes.fromhex(salt_hex)
        # 使用相同的盐值和迭代次数重新计算哈希
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000
        )
        # 安全比较（防止时序攻击）
        return key.hex() == key_hex
    except Exception as e:
        logger.error(f"密码验证失败: {e}")
        return False


def create_access_token(user_id: int, username: str, role: str) -> str:
    """
    生成 JWT 访问令牌

    参数:
        user_id: 用户ID
        username: 用户名
        role: 用户角色（user/admin）

    返回:
        JWT Token 字符串
    """
    current_time = int(time.time())
    payload = {
        'user_id': user_id,        # 用户ID
        'username': username,       # 用户名
        'role': role,               # 角色
        'exp': current_time + settings.JWT_EXPIRE_HOURS * 3600,  # 过期时间
        'iat': current_time         # 签发时间
    }
    token = jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
    logger.info(f"为用户 {username} 生成 JWT Token")
    return token


def decode_access_token(token: str) -> dict:
    """
    验证并解码 JWT Token

    参数:
        token: JWT Token 字符串

    返回:
        payload 字典（包含 user_id, username, role 等）

    异常:
        ValueError: Token 过期或无效时抛出
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT Token 已过期")
        raise ValueError("Token 已过期，请重新登录")
    except jwt.InvalidTokenError:
        logger.warning("无效的 JWT Token")
        raise ValueError("无效的 Token，请重新登录")
