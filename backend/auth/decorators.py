"""
劳动合同纠纷智能问答系统 - 认证装饰器（同步版本）
"""
from fastapi import Depends, HTTPException, Header
from auth.jwt_handler import decode_access_token

def get_current_user(authorization: str = Header(...)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="认证方式无效")
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_access_token(token)
        return payload
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

def require_admin(user: dict = Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="权限不足")
    return user