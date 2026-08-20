"""
劳动合同纠纷智能问答系统 - 数据分析接口（SQLite 版本）
"""
from fastapi import APIRouter, Depends
from database import get_db
from models.schemas import OverviewResponse
from auth.decorators import require_admin

router = APIRouter(prefix="/api/analytics", tags=["数据分析"])


@router.get("/overview", response_model=OverviewResponse, summary="系统数据概览")
def get_overview(db=Depends(get_db), user: dict = Depends(require_admin)):
    """获取系统运行数据概览（仅管理员）"""
    cur = db.cursor()

    # 统计用户总数
    cur.execute("SELECT COUNT(*) AS count FROM users")
    total_users = cur.fetchone()["count"]

    # 统计文档总数
    cur.execute("SELECT COUNT(*) AS count FROM documents")
    total_documents = cur.fetchone()["count"]

    # 统计问答总数
    cur.execute("SELECT COUNT(*) AS count FROM chat_history")
    total_questions = cur.fetchone()["count"]

    # 统计研判总数
    cur.execute("SELECT COUNT(*) AS count FROM judge_records")
    total_judgments = cur.fetchone()["count"]

    # 计算平均置信度
    cur.execute("SELECT AVG(confidence) AS avg FROM chat_history WHERE confidence IS NOT NULL")
    avg_result = cur.fetchone()
    avg_confidence = float(avg_result["avg"]) if avg_result["avg"] else 0.0

    # 查询最近10条问答记录
    cur.execute("""
        SELECT
            ch.id,
            ch.question,
            ch.answer,
            ch.confidence,
            ch.created_at,
            u.username
        FROM chat_history ch
        LEFT JOIN users u ON ch.user_id = u.id
        ORDER BY ch.created_at DESC
        LIMIT 10
    """)
    recent_questions = []
    for row in cur.fetchall():
        row_dict = dict(row)
        recent_questions.append(row_dict)

    # 查询近7天每日问答数量趋势
    cur.execute("""
        SELECT
            DATE(created_at) AS date,
            COUNT(*) AS count
        FROM chat_history
        WHERE created_at >= DATE('now', '-7 days', 'localtime')
        GROUP BY DATE(created_at)
        ORDER BY date
    """)
    question_trend = []
    for row in cur.fetchall():
        row_dict = dict(row)
        question_trend.append(row_dict)

    cur.close()

    return OverviewResponse(
        total_users=total_users,
        total_documents=total_documents,
        total_questions=total_questions,
        total_judgments=total_judgments,
        avg_confidence=round(avg_confidence, 4),
        recent_questions=recent_questions,
        question_trend=question_trend
    )
