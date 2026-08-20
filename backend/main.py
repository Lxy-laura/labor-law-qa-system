"""
劳动合同纠纷智能问答系统 - FastAPI 入口

功能：
1. 创建 FastAPI 应用实例
2. 配置 CORS 跨域
3. 注册所有 API 路由（认证、问答、研判、知识库、数据分析）
4. 应用启动时初始化数据库
5. 提供根路径和健康检查接口
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings

# 配置日志输出格式
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    启动时：初始化数据库
    关闭时：记录日志
    """
    logger.info("=" * 60)
    logger.info("劳动合同纠纷智能问答系统启动中...")
    logger.info("=" * 60)

    # 初始化数据库（创建表和索引）
    try:
        from database import init_db
        init_db()
        logger.info("数据库初始化成功")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        logger.warning("系统将以降级模式运行（数据库功能不可用）")

    logger.info("系统启动完成，等待请求...")
    yield

    logger.info("=" * 60)
    logger.info("劳动合同纠纷智能问答系统关闭")
    logger.info("=" * 60)


# 创建 FastAPI 应用实例
app = FastAPI(
    title="劳动合同纠纷智能问答系统",
    description="""
基于 RAG + LoRA 微调 + DeepSeek API 的劳动合同纠纷智能问答系统。

## 核心功能
- **智能问答**：基于《劳动合同法》的 RAG 检索增强生成
- **合同研判**：逐条分析合同条款的法律风险
- **知识库管理**：法律法规文档的上传、检索和管理
- **数据分析**：系统运行数据概览

## 技术架构
- 检索管线：术语扩展 → Milvus 向量检索 + BM25 → RRF 融合 → Cross-Encoder 重排序
- 生成模型：DeepSeek API（通过 openai SDK 调用）
- 向量模型：BAAI/bge-small-zh-v1.1（支持 LoRA 微调）
- 数据存储：PostgreSQL（业务数据）+ Milvus（向量数据）
    """,
    version="1.0.0",
    lifespan=lifespan
)

# ========== CORS 跨域配置 ==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # 生产环境请指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== 注册 API 路由 ==========
from api.auth import router as auth_router
from api.qa import router as qa_router
from api.judge import router as judge_router
from api.kb import router as kb_router
from api.analytics import router as analytics_router

app.include_router(auth_router)
app.include_router(qa_router)
app.include_router(judge_router)
app.include_router(kb_router)
app.include_router(analytics_router)


# ========== 基础接口 ==========

@app.get("/", summary="系统信息")
def root():
    """根路径 - 返回系统信息和可用接口列表"""
    return {
        "system": "劳动合同纠纷智能问答系统",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "认证": {
                "注册": "POST /api/auth/register",
                "登录": "POST /api/auth/login"
            },
            "问答": {
                "提问": "POST /api/qa/ask",
                "反馈": "POST /api/qa/feedback"
            },
            "研判": {
                "合同分析": "POST /api/judge/analyze"
            },
            "知识库": {
                "文档列表": "GET /api/kb/documents",
                "上传文档": "POST /api/kb/upload",
                "删除文档": "DELETE /api/kb/documents/{id}"
            },
            "数据分析": {
                "系统概览": "GET /api/analytics/overview"
            }
        }
    }


@app.get("/health", summary="健康检查")
def health_check():
    """健康检查接口"""
    return {"status": "healthy"}


# ========== 启动入口 ==========

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG
    )
