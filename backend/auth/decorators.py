"""
劳动合同纠纷智能问答系统 - 认证装饰器

提供 FastAPI 依赖注入函数，用于接口鉴权：
1. get_current_user - 验证登录状态（所有需要登录的接口使用）
2. require_admin - 验证管理员权限（仅管理员可访问的接口使用）
"""
from fastapi import Depends, HTTPException, Header
from auth.jwt_handler import decode_access_token


async def get_current_user(authorization: str = Header(...)):
    """
    从请求头 Authorization 中解析 JWT Token，返回当前用户信息

    用法（FastAPI 依赖注入）:
        @router.get("/example")
        def example(user: dict = Depends(get_current_user)):
            ...

    参数:
        authorization: 请求头中的 Authorization 字段，格式为 "Bearer <token>"

    返回:
        用户信息字典（包含 user_id, username, role）

    异常:
        401: 未提供 Token / Token 格式错误 / Token 无效或过期
    """
    # 验证认证方式
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="认证方式无效，请使用 Bearer Token 格式"
        )

    # 提取 Token
    token = authorization.split(" ", 1)[1]

    # 解码验证
    try:
        payload = decode_access_token(token)
        return payload
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


async def require_admin(user: dict = Depends(get_current_user)):
    """
    管理员权限验证装饰器

    只有 role=admin 的用户才能通过，否则返回 403

    用法:
        @router.delete("/example/{id}")
        def example(id: int, user: dict = Depends(require_admin)):
            ...

    返回:
        用户信息字典（已验证为管理员）

    异常:
        403: 非管理员用户访问
    """
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="权限不足，此操作需要管理员权限"
        )
    return user
