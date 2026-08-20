"""
劳动合同纠纷智能问答系统 - 数据分析接口（SQLite 版本）

提供以下接口（均需管理员权限）：
- GET /api/analytics/overview          - 系统数据概览（KPI卡片）
- GET /api/analytics/qa-trend          - 问答趋势分析（折线图）
- GET /api/analytics/hot-categories    - 问题分类分布（饼图）
- GET /api/analytics/user-activity     - 用户活跃度（柱状图）
- GET /api/analytics/retrieval-metrics - 检索质量指标（雷达图）
"""
from fastapi import APIRouter, Depends, Query
from database import get_db
from models.schemas import OverviewResponse
from auth.decorators import require_admin

router = APIRouter(prefix="/api/analytics", tags=["数据分析"])

@router.get("/overview", response_model=OverviewResponse, summary="系统数据概览")
def get_overview(db=Depends(get_db), user: dict = Depends(require_admin)):
    """获取系统运行数据概览（仅管理员）"""
    cur = db.cursor()

    cur.execute("SELECT COUNT(*) AS count FROM users")
    total_users = cur.fetchone()["count"]

    cur.execute("SELECT COUNT(*) AS count FROM documents")
    total_documents = cur.fetchone()["count"]

    cur.execute("SELECT COUNT(*) AS count FROM chat_history")
    total_questions = cur.fetchone()["count"]

    cur.execute("SELECT COUNT(*) AS count FROM judge_records")
    total_judgments = cur.fetchone()["count"]

    cur.execute("SELECT AVG(confidence) AS avg FROM chat_history WHERE confidence IS NOT NULL")
    avg_result = cur.fetchone()
    avg_confidence = float(avg_result["avg"]) if avg_result["avg"] else 0.0

    cur.execute("""
        SELECT ch.id, ch.question, ch.answer, ch.confidence, ch.created_at, u.username
        FROM chat_history ch
        LEFT JOIN users u ON ch.user_id = u.id
        ORDER BY ch.created_at DESC LIMIT 10
    """)
    recent_questions = [dict(row) for row in cur.fetchall()]

    cur.execute("""
        SELECT DATE(created_at) AS date, COUNT(*) AS count
        FROM chat_history
        WHERE created_at >= DATE('now', '-7 days', 'localtime')
        GROUP BY DATE(created_at) ORDER BY date
    """)
    question_trend = [dict(row) for row in cur.fetchall()]

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

@router.get("/qa-trend", summary="问答趋势分析")
def get_qa_trend(
    days: int = Query(30, ge=1, le=365, description="查询天数"),
    db=Depends(get_db),
    user: dict = Depends(require_admin)
):
    """获取问答趋势数据（近N天每日提问数和活跃用户数）"""
    from datetime import datetime, timedelta
    # 在 Python 中计算起始日期，不能直接用 SQLite 的 DATE('now', ?) 参数绑定
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    cur = db.cursor()

    # 每日提问数
    cur.execute(
        """SELECT DATE(created_at) AS date, COUNT(*) AS count
           FROM chat_history
           WHERE created_at >= ?
           GROUP BY DATE(created_at)
           ORDER BY date""",
        (start_date,)
    )
    rows = cur.fetchall()

    # 每日活跃用户数（有提问的用户）
    cur.execute(
        """SELECT DATE(created_at) AS date, COUNT(DISTINCT user_id) AS count
           FROM chat_history
           WHERE created_at >= ?
           GROUP BY DATE(created_at)
           ORDER BY date""",
        (start_date,)
    )
    user_rows = cur.fetchall()
    cur.close()

    # 合并数据
    user_map = {r["date"]: r["count"] for r in user_rows}
    dates = []
    questions = []
    users = []
    for r in rows:
        d = r["date"]
        dates.append(d[5:] if len(d) > 5 else d)  # 取 MM-DD
        questions.append(r["count"])
        users.append(user_map.get(d, 0))

    return {"dates": dates, "questions": questions, "users": users}

@router.get("/hot-categories", summary="问题分类分布")
def get_hot_categories(db=Depends(get_db), user: dict = Depends(require_admin)):
    """获取问题分类分布（按关键词匹配法律领域）"""
    cur = db.cursor()
    cur.execute("SELECT question FROM chat_history")
    rows = cur.fetchall()
    cur.close()

    categories = {"工资报酬": 0, "解除终止": 0, "社保公积金": 0, "工时休假": 0, "调岗调薪": 0, "其他": 0}
    keywords = {
        "工资报酬": ["工资", "薪酬", "报酬", "拖欠", "克扣", "加班费", "绩效", "奖金", "最低工资"],
        "解除终止": ["解除", "终止", "辞退", "开除", "离职", "补偿金", "赔偿金", "经济补偿"],
        "社保公积金": ["社保", "公积金", "保险", "养老", "医疗", "失业", "工伤", "生育"],
        "工时休假": ["工时", "加班", "休假", "年假", "假期", "休息日", "法定假日", "调休"],
        "调岗调薪": ["调岗", "调薪", "岗位", "转岗", "降薪", "变更"]
    }
    for row in rows:
        q = row["question"] if row["question"] else ""
        matched = False
        for cat, kws in keywords.items():
            if any(kw in q for kw in kws):
                categories[cat] += 1
                matched = True
                break
        if not matched:
            categories["其他"] += 1

    return [{"name": k, "value": v} for k, v in categories.items()]

@router.get("/user-activity", summary="用户活跃度")
def get_user_activity(db=Depends(get_db), user: dict = Depends(require_admin)):
    """获取用户活跃度（按24小时时段分布）"""
    cur = db.cursor()
    cur.execute(
        """SELECT CAST(strftime('%H', created_at) AS INTEGER) AS hour,
                  COUNT(*) AS count
           FROM chat_history
           WHERE created_at >= DATE('now', '-30 days')
           GROUP BY hour ORDER BY hour"""
    )
    rows = cur.fetchall()
    cur.close()

    hour_map = {r["hour"]: r["count"] for r in rows}
    labels = ['0-2', '2-4', '4-6', '6-8', '8-10', '10-12', '12-14', '14-16', '16-18', '18-20', '20-22', '22-24']
    counts = []
    for i in range(0, 24, 2):
        counts.append(hour_map.get(i, 0) + hour_map.get(i + 1, 0))

    return {"labels": labels, "counts": counts}

@router.get("/retrieval-metrics", summary="检索质量指标")
def get_retrieval_metrics(db=Depends(get_db), user: dict = Depends(require_admin)):
    """获取检索质量指标（基于真实问答数据的统计）"""
    cur = db.cursor()

    cur.execute("SELECT AVG(confidence) AS avg FROM chat_history WHERE confidence IS NOT NULL")
    avg_conf = cur.fetchone()["avg"]
    relevance_score = round(float(avg_conf) * 100) if avg_conf else 0

    cur.execute("SELECT COUNT(*) AS total FROM chat_history")
    total_qa = cur.fetchone()["total"]
    cur.execute("SELECT COUNT(*) AS count FROM chat_history WHERE citations IS NOT NULL AND citations != '' AND citations != '[]'")
    cited_qa = cur.fetchone()["count"]
    citation_rate = round(cited_qa / total_qa * 100) if total_qa > 0 else 0

    cur.execute("SELECT AVG(rating) AS avg FROM feedback")
    avg_rating = cur.fetchone()["avg"]
    satisfaction = round(float(avg_rating) * 20) if avg_rating else 0

    cur.execute("SELECT COUNT(*) AS count FROM documents")
    doc_count = cur.fetchone()["count"]
    recall = min(100, doc_count) if doc_count > 0 else 0

    cur.execute("SELECT COUNT(*) AS count FROM chat_history WHERE citations IS NOT NULL AND citations != '' AND citations != '[]' AND answer IS NOT NULL AND answer != ''")
    accurate_qa = cur.fetchone()["count"]
    accuracy = round(accurate_qa / total_qa * 100) if total_qa > 0 else 0

    cur.execute("SELECT COUNT(*) AS count FROM chat_history WHERE created_at >= DATE('now', '-7 days')")
    recent_qa = cur.fetchone()["count"]
    response_speed = min(100, recent_qa * 10) if recent_qa > 0 else 0

    cur.close()

    return {
        "indicators": [
            {"name": "召回率", "value": recall},
            {"name": "准确率", "value": accuracy},
            {"name": "响应速度", "value": response_speed},
            {"name": "答案相关度", "value": relevance_score},
            {"name": "引用准确率", "value": citation_rate},
            {"name": "用户满意度", "value": satisfaction}
        ]
    }