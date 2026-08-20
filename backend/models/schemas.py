"""
劳动合同纠纷智能问答系统 - Pydantic 数据模型

定义所有 API 接口的请求和响应数据结构，包括：
- 认证请求/响应（注册、登录、Token）
- 问答请求/响应（问题、回答、引用、案例、落地服务）
- 研判请求/响应（合同文本、条款分析、风险报告）
- 知识库管理请求/响应（文档列表、上传、删除）
- 数据分析响应（系统概览）
- 反馈请求/响应
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# ========================================================================
#  认证相关模型
# ========================================================================

class RegisterRequest(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    email: str = Field(..., description="邮箱地址")
    password: str = Field(..., min_length=6, max_length=100, description="密码（至少6位）")


class LoginRequest(BaseModel):
    """用户登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class TokenResponse(BaseModel):
    """JWT Token 响应"""
    access_token: str = Field(..., description="JWT 访问令牌")
    token_type: str = Field("bearer", description="令牌类型")
    user_id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    role: str = Field(..., description="用户角色（user/admin）")


# ========================================================================
#  问答相关模型
# ========================================================================

class QuestionRequest(BaseModel):
    """智能问答请求"""
    question: str = Field(..., description="用户的劳动合同纠纷问题")
    top_k: Optional[int] = Field(5, description="返回结果数量", ge=1, le=20)


class Citation(BaseModel):
    """法条引用"""
    law: str = Field(..., description="法律名称（如：劳动合同法）")
    article: str = Field(..., description="条款编号（如：第十九条）")
    content: str = Field(..., description="条款原文内容")
    relevance: float = Field(..., description="相关度分数（0-1）")


class CaseExample(BaseModel):
    """案例参考"""
    title: str = Field(..., description="案例标题")
    summary: str = Field(..., description="案例摘要")
    court: str = Field(..., description="审理法院")


class LandingService(BaseModel):
    """落地服务推荐"""
    service_type: str = Field(..., description="服务类型（如：工资拖欠、违法解除）")
    hotline: Optional[str] = Field(None, description="维权热线电话")
    institution: Optional[str] = Field(None, description="推荐维权机构")
    address: Optional[str] = Field(None, description="机构地址")
    action_guide: List[str] = Field(default_factory=list, description="行动指引步骤")


class AnswerResponse(BaseModel):
    """智能问答响应"""
    answer: str = Field(..., description="回答内容")
    citations: List[Citation] = Field(default_factory=list, description="法条引用列表")
    cases: List[CaseExample] = Field(default_factory=list, description="案例参考列表")
    landing_services: List[LandingService] = Field(default_factory=list, description="落地服务列表")
    confidence: float = Field(..., description="置信度（0-1）")
    expanded_query: Optional[str] = Field(None, description="同义词扩展后的查询")


# ========================================================================
#  合同研判相关模型
# ========================================================================

class JudgeRequest(BaseModel):
    """合同研判请求"""
    contract_text: str = Field(..., description="劳动合同全文文本")


class ClauseAnalysis(BaseModel):
    """单条条款分析结果"""
    clause_index: int = Field(..., description="条款序号")
    clause_text: str = Field(..., description="条款原文")
    risk_level: str = Field(..., description="风险等级：低/中/高")
    risk_description: str = Field(..., description="风险描述")
    legal_basis: List[str] = Field(default_factory=list, description="法律依据列表")
    suggestion: str = Field(..., description="修改建议")


class JudgeResponse(BaseModel):
    """合同研判响应"""
    total_clauses: int = Field(..., description="条款总数")
    risk_summary: Dict[str, int] = Field(..., description="风险等级统计（高/中/低）")
    clauses: List[ClauseAnalysis] = Field(default_factory=list, description="逐条分析结果")
    overall_assessment: str = Field(..., description="总体评估")


# ========================================================================
#  知识库管理相关模型
# ========================================================================

class DocumentInfo(BaseModel):
    """文档信息"""
    id: int
    title: str
    doc_type: Optional[str] = None
    chunk_count: int = 0
    created_at: datetime


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    documents: List[DocumentInfo]
    total: int


class UploadResponse(BaseModel):
    """文档上传响应"""
    document_id: int
    title: str
    chunk_count: int
    message: str


# ========================================================================
#  数据分析相关模型
# ========================================================================

class OverviewResponse(BaseModel):
    """系统数据概览响应"""
    total_users: int = Field(..., description="用户总数")
    total_documents: int = Field(..., description="文档总数")
    total_questions: int = Field(..., description="问答总数")
    total_judgments: int = Field(..., description="研判总数")
    avg_confidence: float = Field(..., description="平均置信度")
    recent_questions: List[Dict[str, Any]] = Field(default_factory=list, description="最近问答记录")
    question_trend: List[Dict[str, Any]] = Field(default_factory=list, description="问答趋势（近7天）")


# ========================================================================
#  反馈相关模型
# ========================================================================

class FeedbackRequest(BaseModel):
    """问答反馈请求"""
    chat_id: int = Field(..., description="对话记录ID")
    rating: int = Field(..., ge=1, le=5, description="评分（1-5）")
    comment: Optional[str] = Field(None, description="反馈评论")


class FeedbackResponse(BaseModel):
    """反馈响应"""
    message: str
    feedback_id: int
