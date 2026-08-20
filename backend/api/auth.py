"""
劳动合同纠纷智能问答系统 - 认证接口（SQLite 版本）

提供用户注册和登录功能：
- POST /api/auth/register - 用户注册
- POST /api/auth/login    - 用户登录
"""
from fastapi import APIRouter, Depends, HTTPException
from database import get_db
from models.schemas import RegisterRequest, LoginRequest, TokenResponse
from auth.jwt_handler import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", response_model=TokenResponse, summary="用户注册")
def register(req: RegisterRequest, db=Depends(get_db)):
    """用户注册接口"""
    cur = db.cursor()

    # 检查用户名是否已存在
    cur.execute("SELECT id FROM users WHERE username = ?", (req.username,))
    if cur.fetchone():
        cur.close()
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 检查邮箱是否已被注册
    cur.execute("SELECT id FROM users WHERE email = ?", (req.email,))
    if cur.fetchone():
        cur.close()
        raise HTTPException(status_code=400, detail="该邮箱已被注册")

    # 对密码进行哈希处理后存入数据库
    password_hash = hash_password(req.password)

    # 创建新用户
    cur.execute(
        "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
        (req.username, req.email, password_hash, "user")
    )
    db.commit()
    user_id = cur.lastrowid
    cur.close()

    # 生成 JWT Token
    token = create_access_token(user_id, req.username, "user")

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user_id,
        username=req.username,
        role="user"
    )


@router.post("/login", response_model=TokenResponse, summary="用户登录")
def login(req: LoginRequest, db=Depends(get_db)):
    """用户登录接口"""
    cur = db.cursor()

    # 查询用户
    cur.execute(
        "SELECT id, username, password_hash, role FROM users WHERE username = ?",
        (req.username,)
    )
    user = cur.fetchone()
    cur.close()

    # 用户不存在
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 验证密码
    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 生成 JWT Token
    token = create_access_token(user["id"], user["username"], user["role"])

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user["id"],
        username=user["username"],
        role=user["role"]
    )
